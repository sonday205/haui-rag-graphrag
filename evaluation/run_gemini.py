"""Chạy Gemini có checkpoint sau từng lượt; không ghi hoặc hiển thị API key."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from src.project import ROOT, Searcher, answer, pipeline_sha256, read_jsonl, effective_config, index_fingerprint, runtime_versions
from src.index_store import sha256

OUT = ROOT / "evaluation/runs/gemini_checkpoint.jsonl"
META = ROOT / "evaluation/runs/gemini_meta.json"
PACE = ROOT / "evaluation/runs/gemini_pacing.json"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ids", nargs="+", help="Nếu quota thấp, chọn cùng ID cho cả hai pipeline")
    parser.add_argument("--questions-file", choices=("questions.jsonl", "questions_multidoc_ocr.jsonl", "questions_research_20261001.jsonl"),
                        default="questions.jsonl", help="Bộ câu hỏi đánh giá trong thư mục evaluation")
    parser.add_argument("--run-id", default="checkpoint", help="Tên run riêng khi corpus/chỉ mục thay đổi")
    parser.add_argument("--retry-errors", action="store_true")
    parser.add_argument("--allow-code-change", action="store_true",
                        help="Chỉ dùng khi đã xác nhận thay đổi mã không ảnh hưởng phép so sánh")
    parser.add_argument("--max-new-calls", type=int, help="Dừng sau số lượt gọi mới để kiểm tra dịch vụ")
    parser.add_argument("--min-interval-seconds", type=float, default=5.0,
                        help="Khoảng cách giữa thời điểm bắt đầu hai request; mặc định 5 giây (~12/phút)")
    args = parser.parse_args()
    if not args.run_id.replace("_", "").isalnum():
        raise SystemExit("--run-id chỉ nhận chữ, số và dấu gạch dưới")
    out = OUT if args.run_id == "checkpoint" else ROOT / f"evaluation/runs/gemini_{args.run_id}.jsonl"
    meta = META if args.run_id == "checkpoint" else ROOT / f"evaluation/runs/gemini_{args.run_id}_meta.json"
    if args.min_interval_seconds < 4.5:
        raise SystemExit("Để giữ dưới 15 lời gọi/phút, --min-interval-seconds phải từ 4.5 trở lên")
    if args.max_new_calls is not None and args.max_new_calls < 0:
        raise SystemExit("--max-new-calls không được âm")
    if not os.getenv("GEMINI_API_KEY"):
        raise SystemExit("Chưa có GEMINI_API_KEY trong .env")
    questions_path = ROOT / "evaluation" / args.questions_file
    questions = read_jsonl(questions_path)
    if args.ids:
        unknown = set(args.ids) - {q["question_id"] for q in questions}
        if unknown:
            raise SystemExit(f"ID không tồn tại: {sorted(unknown)}")
        questions = [q for q in questions if q["question_id"] in args.ids]
    if not questions or len({q["question_id"] for q in questions}) != len(questions):
        raise SystemExit("Bộ câu hỏi rỗng hoặc trùng ID")
    searcher = Searcher()
    if any(not set(q["gold_article_ids"]) <= set(searcher.by_id) for q in questions):
        raise SystemExit("Gold ID nằm ngoài corpus")
    fingerprint = {
        "questions_file": args.questions_file,
        "questions_sha256": hashlib.sha256(questions_path.read_bytes()).hexdigest(),
        "code_sha256": pipeline_sha256(),
        **index_fingerprint(searcher.directory),
        "config": effective_config(), "runtime_versions": runtime_versions(),
        "runner_sha256": sha256(Path(__file__)),
        "method_order": "alternating_by_question_v1",
        "min_interval_seconds": args.min_interval_seconds,
        "selected_question_ids": [q["question_id"] for q in questions],
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    existing_meta = meta.exists()
    if existing_meta:
        previous = json.loads(meta.read_text())
        if any(previous.get(k) != value for k, value in fingerprint.items() if k != "code_sha256"):
            raise SystemExit("Checkpoint thuộc cấu hình/corpus khác; giữ file cũ và tạo run mới trước khi tiếp tục")
    else:
        if out.exists() and out.stat().st_size:
            raise SystemExit("Checkpoint có dữ liệu nhưng thiếu metadata; không tự tiếp tục")
        meta.write_text(json.dumps({**fingerprint, "started_utc": datetime.now(timezone.utc).isoformat()}, ensure_ascii=False, indent=2))
        meta.with_name(meta.stem + "_questions.jsonl").write_text("".join(json.dumps(q, ensure_ascii=False) + "\n" for q in questions))
    completed = {}
    if out.exists():
        for row in read_jsonl(out):
            completed[(row["question_id"], row["method"])] = row
    if not args.retry_errors and any(
        any(word in (row["response"]["error"] or "").lower() for word in ("429", "resource_exhausted", "quota"))
        for row in completed.values()
    ):
        print("Checkpoint có lỗi quota; chỉ chạy lại với --retry-errors sau khi hạn mức được khôi phục.")
        return
    if existing_meta and previous.get("code_sha256") != fingerprint["code_sha256"] and not args.allow_code_change:
        raise SystemExit("Mã pipeline đã đổi; tạo --run-id mới hoặc kiểm tra kỹ rồi dùng --allow-code-change")
    if existing_meta and previous.get("code_sha256") != fingerprint["code_sha256"]:
        revisions = previous.setdefault("resumed_code_sha256", [])
        if fingerprint["code_sha256"] not in revisions:
            revisions.append(fingerprint["code_sha256"])
            meta.write_text(json.dumps(previous, ensure_ascii=False, indent=2))
            print("Lưu ý: mã nguồn khác SHA run đầu; kiểm tra thay đổi trước khi gộp kết quả.", flush=True)
    # Làm nóng cả hai phương pháp; không phát sinh lượt Gemini.
    for method in ("rag", "graph_rag"):
        searcher.retrieve(questions[0]["question"], method)
    new_calls = 0
    consecutive_service_errors = 0
    for index, question in enumerate(questions):
        methods = ("rag", "graph_rag") if index % 2 == 0 else ("graph_rag", "rag")
        for method in methods:
            if args.max_new_calls is not None and new_calls >= args.max_new_calls:
                print(f"Đã dừng theo --max-new-calls={args.max_new_calls}.", flush=True)
                return
            key = question["question_id"], method
            if key in completed and (not args.retry_errors or not completed[key]["response"]["error"]):
                continue
            started_epoch = time.time()
            response = answer(question["question"], method, searcher, min_interval_seconds=args.min_interval_seconds)
            new_calls += 1
            row = {"question_id": key[0], "method": method,
                   "started_utc": datetime.fromtimestamp(started_epoch, timezone.utc).isoformat(),
                   "finished_utc": datetime.now(timezone.utc).isoformat(), "response": response}
            with out.open("a") as file:
                file.write(json.dumps(row, ensure_ascii=False) + "\n")
                file.flush()
                os.fsync(file.fileno())
            completed[key] = row
            print(json.dumps({"question_id": key[0], "method": method,
                "latency_ms": response["latency_ms"], "token_usage": response["token_usage"],
                "error": response["error"]}, ensure_ascii=False), flush=True)
            detail = (response["error"] or "").lower()
            consecutive_service_errors = consecutive_service_errors + 1 if "503" in detail or "unavailable" in detail else 0
            if consecutive_service_errors >= 2:
                print("Dừng sau hai lỗi 503 liên tiếp; chờ dịch vụ ổn định trước khi thử tiếp.", flush=True)
                return
            if any(word in detail for word in ("429", "resource_exhausted", "quota", "403", "permission_denied")):
                print("Dừng tại giới hạn/quyền API; checkpoint đã lưu.", flush=True)
                return
    print(f"Hoàn tất {len(completed)} lượt trong {out}")


if __name__ == "__main__":
    main()
