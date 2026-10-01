"""Tạo một báo cáo Markdown từ checkpoint thật và phiếu chấm tay."""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median

from src.project import ROOT, read_jsonl

RUN = ROOT / "evaluation/runs/gemini_checkpoint.jsonl"
SCORES = ROOT / "evaluation/manual_scores.json"
DEST = ROOT / "evaluation/BAO_CAO_DANH_GIA_GEMINI.md"
METHODS = ("rag", "graph_rag")
LABELS = {"rag": "RAG vector", "graph_rag": "GraphRAG cấu trúc"}


def quote(value: str | None) -> str:
    return "\n".join("> " + line for line in (value or "*Không có câu trả lời hợp lệ.*").splitlines())


def main():
    questions = {q["question_id"]: q for q in read_jsonl(ROOT / "evaluation/questions.jsonl")}
    scores = json.loads(SCORES.read_text())
    rows = read_jsonl(RUN)
    by_case = defaultdict(dict)
    for row in rows:
        by_case[row["question_id"]][row["method"]] = row
    paired = [qid for qid in questions if qid in by_case and all(method in by_case[qid] and not by_case[qid][method]["response"]["error"] for method in METHODS)]
    if set(paired) != set(scores):
        raise ValueError("Phiếu chấm tay phải khớp chính xác tập câu hỏi đủ hai kết quả")
    valid_latest = sum(not row["response"]["error"] for cases in by_case.values() for row in cases.values())
    failed_latest = [(qid, method, by_case[qid][method]["response"]["error"])
                     for qid in questions for method in METHODS
                     if method in by_case[qid] and by_case[qid][method]["response"]["error"]]
    errors_429 = sum("429" in (row["response"]["error"] or "") for row in rows)
    errors_503 = sum("503" in (row["response"]["error"] or "") for row in rows)
    unrun = [(qid, method) for qid in questions for method in METHODS if method not in by_case[qid]]
    timed_starts = [datetime.fromisoformat(row["started_utc"]) for row in rows if row.get("started_utc")]
    intervals = [(b-a).total_seconds() for a, b in zip(timed_starts, timed_starts[1:])]
    lines = [
        "# Đánh giá Gemini: RAG vector và GraphRAG trên quy chế HaUI",
        "",
        "**Lưu ý phiên bản dữ liệu:** Đây là checkpoint trước khi bổ sung 8 PDF OCR, chỉ dùng corpus 1 PDF/135 đoạn và GraphRAG chủ đề cũ. Không gộp số liệu LLM ở đây với chỉ mục 9 PDF hiện tại; bộ truy xuất mới chưa được chấm câu trả lời Gemini.",
        "",
        f"Tạo lúc {datetime.now(timezone.utc).isoformat()} (UTC). Nguồn số liệu: `evaluation/runs/gemini_checkpoint.jsonl`; phiếu chấm tay: `evaluation/manual_scores.json`.",
        "",
        "## Phạm vi và kết luận ngắn",
        "",
        f"Checkpoint có **{len(paired)}/30 cặp câu hỏi** đủ hai đáp án hợp lệ để chấm, "
        f"{valid_latest} đáp án hợp lệ ở trạng thái cuối, {len(failed_latest)} lượt đang lỗi và {len(unrun)} lượt chưa chạy. "
        f"Tệp thô gồm {len(rows)} lượt API, kể cả các lần thử lại. Cùng model `gemini-3.5-flash-lite`. "
        "Chỉ dùng cặp đủ hai đáp án trong bảng so sánh; đây là checkpoint, chưa phải kết quả đủ 30 câu.",
        "",
        "Kết quả của các nhóm chưa có cặp hợp lệ chưa thể dùng để kết luận phương pháp nào tốt hơn. "
        "Lỗi dịch vụ được ghi riêng khỏi lỗi trả lời hoặc lỗi truy xuất.",
        "",
        "## Thiết lập và cách chấm",
        "",
        "- Corpus: 1 PDF hợp nhất QĐ 744/2021 và 666/2023 trên [SICT HaUI](https://sict.haui.edu.vn/media/29/uffile-upload-no-title29811.pdf), 22 điều, 135 đoạn; hiệu lực hiện hành `unknown`.",
        "- Hai phương pháp dùng cùng bộ câu hỏi, model sinh, prompt tiếng Việt, `temperature=0`, `top_k=5` và giới hạn tối đa 6.500 ký tự chứng cứ. RAG dùng embedding đa ngôn ngữ/cosine; GraphRAG tự thiết kế dùng hạt giống TF-IDF ký tự rồi mở rộng chủ đề/đồ thị.",
        "- Khi tiếp tục checkpoint, mã `src/project.py` tăng độ dài chuỗi lỗi Gemini được lưu và cấu hình SDK tối đa một request HTTP cho mỗi lượt gọi; phiên bản SDK đang cài đã có mặc định một request. Logic truy xuất, prompt, model và nhiệt độ sinh không đổi. Metadata lưu các SHA mã đã dùng.",
        "- Chấm tay theo đáp án chuẩn đã viết trước khi gọi model: **Đúng nội dung** (0/1: ý chính thực tế đúng), **Đủ ý** (0/1: bao phủ cả điều kiện/ngoại lệ trong đáp án chuẩn), **Dẫn đúng nguồn** (0/1: ID đoạn có thật và hỗ trợ phát biểu). Câu từ chối sai trên câu trả lời được nhận 0 ở cả ba cột. Người làm dự án tự chấm, chưa có người phản biện độc lập.",
        "- Recall theo câu: câu có ít nhất một gold ID trong top 5. Độ trễ đo từ đầu truy xuất đến khi có đáp án API, không gồm khởi động/tải model và không đại diện hiệu năng tải cao. Token lấy từ `usage_metadata` của API; không ước tính tiền.",
        f"- Từ lượt tiếp tục, script giãn tối thiểu 5 giây giữa thời điểm bắt đầu hai request (~12 lượt/phút, dưới giới hạn 15). "
        + (f"Khoảng cách thực tế nhỏ nhất trong {len(intervals)} khoảng ghi timestamp: {min(intervals):.2f} giây." if intervals else "Chưa đủ timestamp để xác nhận khoảng cách thực tế."),
        "",
        f"## Bảng tổng hợp trên cùng {len(paired)} câu",
        "",
        "| Thước đo | RAG vector | GraphRAG |",
        "|---|---:|---:|",
    ]
    for metric, label in (("correct", "Đúng nội dung"), ("complete", "Đủ ý"), ("citation", "Dẫn đúng nguồn")):
        counts = [sum(scores[qid][m][metric] for qid in paired) for m in METHODS]
        lines.append(f"| {label} | {counts[0]}/{len(paired)} | {counts[1]}/{len(paired)} |")
    def paired_results(method):
        return [by_case[qid][method]["response"] for qid in paired]
    recall = {}
    for method in METHODS:
        recall[method] = sum(bool(set(questions[qid]["gold_article_ids"]) & set(by_case[qid][method]["response"]["retrieved_article_ids"])) for qid in paired)
    lines.append(f"| Recall@5 (câu có gold trong top 5) | {recall['rag']}/{len(paired)} | {recall['graph_rag']}/{len(paired)} |")
    for title, fn, suffix in (("Độ trễ trung bình", mean, " ms"), ("Độ trễ trung vị", median, " ms")):
        values = [fn(r["latency_ms"] for r in paired_results(m)) for m in METHODS]
        lines.append(f"| {title} | {values[0]:.2f}{suffix} | {values[1]:.2f}{suffix} |")
    for key, label in (("input", "Token đầu vào"), ("output", "Token đầu ra"), ("total", "Tổng token")):
        values = [sum(r["token_usage"][key] or 0 for r in paired_results(m)) for m in METHODS]
        lines.append(f"| {label} | {values[0]:,} | {values[1]:,} |")
    lines += [
        "",
        "Độ dài chứng cứ truy xuất có thể khác dù cùng `top_k` và mức trần ký tự. "
        "Không thể quy toàn bộ khác biệt độ trễ/token cho cấu trúc truy xuất. Chưa tính thời gian xây chỉ mục, công sức duyệt dữ liệu hoặc chi phí tiền tệ.",
        "",
        "## Từng câu hỏi, câu trả lời và bằng chứng",
        "",
    ]
    for qid in paired:
        question = questions[qid]
        lines += [f"### {qid} — {question['question']}", "", f"**Đáp án chuẩn:** {question['gold_answer']}", "",
                  f"**Gold ID:** `{', '.join(question['gold_article_ids'])}`", ""]
        for method in METHODS:
            response = by_case[qid][method]["response"]
            score = scores[qid][method]
            usage = response["token_usage"] or {}
            cited = ", ".join(f"[{c['article_id']}]({c['url']})" for c in response["citations"]) or "Không có"
            retrieved = ", ".join(f"`{item}`" for item in response["retrieved_article_ids"])
            lines += [f"**{LABELS[method]} — {sum(score[k] for k in ('correct','complete','citation'))}/3** "
                      f"(đúng {score['correct']}, đủ {score['complete']}, dẫn {score['citation']})", "",
                      quote(response["answer"]), "", f"Nguồn dẫn: {cited}.  ",
                      f"ID truy xuất: {retrieved}.  ",
                      f"Độ trễ: {response['latency_ms']:.2f} ms; API: {response['api_calls']}; "
                      f"token vào/ra/tổng: {usage.get('input')}/{usage.get('output')}/{usage.get('total')}.  ",
                      f"Nhận xét chấm tay: {score['note']}", ""]
    lines += ["## Lượt không ghép cặp và lỗi dịch vụ", "",
              f"Trên {len(rows)} lượt API đã ghi: {sum(not row['response']['error'] for row in rows)} lượt có đáp án, "
              f"{errors_429} lượt `429`, {errors_503} lượt `503`. Các lần thử lỗi vẫn được giữ trong checkpoint; "
              "bảng dưới hiển thị trạng thái mới nhất của mỗi cặp câu hỏi và phương pháp.", ""]
    for qid in questions:
        if qid not in by_case or qid in paired:
            continue
        question = questions[qid]
        lines += [f"### {qid} — {question['question']}", "", f"Đáp án chuẩn: {question['gold_answer']}", ""]
        for method in METHODS:
            if method not in by_case[qid]:
                lines += [f"- {LABELS[method]}: chưa chạy."]
                continue
            response = by_case[qid][method]["response"]
            lines += [f"- {LABELS[method]}: " + ("lỗi API, không có đáp án hợp lệ" if response["error"] else "có đáp án nhưng không đưa vào bảng so sánh vì thiếu cặp tương ứng") +
                      f"; {response['latency_ms']:.2f} ms; lỗi: `{response['error'] or 'không'}`."]
            if response["answer"]:
                lines += ["", quote(response["answer"]), ""]
        lines.append("")
    lines += [
        "## Nhận xét và giới hạn cho báo cáo học phần",
        "",
        "- Lần chạy đầu chỉ nghỉ 0,7 giây sau mỗi lượt và không kiểm soát số lần bắt đầu trong một phút. Đây là thiếu sót ở code có thể góp phần gây `429`, nhưng bản ghi cũ không có timestamp và nội dung lỗi bị cắt nên không xác định được 429 do RPM, TPM hay hạn mức ngày. Script hiện giãn tối thiểu 5 giây/lượt và cấu hình SDK một HTTP request/lượt.",
        "- S05: GraphRAG tìm đúng Điều 9 khoản 1 và trả lời; RAG bỏ lỡ đoạn này nên từ chối sai. S07: tình huống ngược lại với khoảng điểm A/F ở Điều 9 khoản 7. Hai ví dụ cho thấy lỗi truy xuất chuyển thẳng thành lỗi trả lời dù cùng model sinh.",
        "- S02 và S04: cả hai trả đúng ý chính nhưng lược bỏ điều kiện trong đáp án chuẩn (học phí khi rút học phần; ngoại lệ bất khả kháng của giới hạn học trực tuyến). Vì vậy điểm **đủ ý** thấp hơn điểm **đúng nội dung**.",
        f"- Tập chấm hiện có {len(paired)} cặp; người viết và chấm gold là cùng một người, có nguy cơ thiên lệch. Cần người phản biện độc lập trước khi dùng làm kết luận mạnh.",
        "- Lần thử ban đầu gặp `429 RESOURCE_EXHAUSTED` ở S08 GraphRAG. Khi tiếp tục với giãn 5 giây, Gemini trả `503 UNAVAILABLE` liên tiếp. Một lượt kiểm chứng sau khi cấu hình SDK chỉ gửi một request HTTP vẫn trả 503. Đây là lỗi dịch vụ/model quá tải theo nội dung phản hồi, không có bằng chứng do code hoặc vượt giới hạn 15 lượt/phút. Giữ nguyên từng lần thử trong checkpoint.",
        "- Khi dịch vụ ổn định, tiếp tục bằng `python -m evaluation.run_gemini --retry-errors` với cùng corpus/config; sau khi có các cặp mới, chấm tay vào `manual_scores.json` rồi chạy `python -m evaluation.write_gemini_report`. Không cộng điểm của câu chưa chấm.",
        "",
        "## Tài liệu kiểm chứng",
        "",
        "- [PDF quy chế hợp nhất HaUI](https://sict.haui.edu.vn/media/29/uffile-upload-no-title29811.pdf).",
        "- `evaluation/questions.jsonl`: câu hỏi, đáp án chuẩn, gold ID.",
        "- `evaluation/runs/gemini_checkpoint.jsonl`: đầu ra nguyên bản, đoạn truy xuất, trace, lỗi và token theo lượt.",
        "- `evaluation/manual_scores.json`: điểm và lý do chấm từng đáp án.",
    ]
    DEST.write_text("\n".join(lines) + "\n")
    print(f"{DEST}: {len(paired)} cặp, {len(rows)} lượt đã ghi")


if __name__ == "__main__":
    main()
