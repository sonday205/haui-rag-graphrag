"""Đánh giá nhỏ có trace và baseline hybrid, không gọi Gemini khi truy xuất."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from statistics import mean, median

from src.project import ROOT, Searcher, answer, effective_config, index_fingerprint, pipeline_sha256, read_jsonl, runtime_versions, validate_generation

METHODS = ("rag", "hybrid", "graph_rag")
LABELS = {"rag": "RAG vector", "hybrid": "Hybrid không graph", "graph_rag": "GraphRAG"}
DEST = ROOT / "evaluation/runs/research_20261001"
QUESTIONS = ROOT / "evaluation/questions_research_20261001.jsonl"
LIVE = ROOT / "evaluation/runs/gemini_research_20261001_35lite.jsonl"
VALIDATED = DEST / "generation_revalidated.json"


def revalidate():
    """Kiểm tra lại JSON đã nhận, không tạo/thử lại câu trả lời hoặc gọi model."""
    rows = []
    for original in read_jsonl(LIVE):
        row = json.loads(json.dumps(original))
        response = row["response"]
        old_error = response["error"]
        if response.get("raw_answer") and (not old_error or "ValueError" in old_error):
            try:
                checked = validate_generation(response["raw_answer"], response["retrieved_article_ids"])
                response["answer"] = checked["answer"]
                response["answer_status"] = checked["status"]
                response["error"] = None
                evidence = {e["id"]: e for e in response["evidence"]}
                # Label sử dụng cùng metadata đã lưu trong request gốc.
                response["citations"] = []
                for ident in checked["cited_ids"]:
                    e = evidence[ident]
                    label = e["title"]
                    if e.get("article_number"):
                        label += f", Điều {e['article_number']}"
                        if e.get("clause") not in (None, "title"): label += f", khoản {e['clause']}"
                    label += f", trang {e['page_start']}"
                    if e.get("extraction_method") == "user_supplied_ocr": label += " (OCR chưa hiệu đính toàn bộ)"
                    response["citations"].append({"article_id": ident, "label": label, "url": e["source_url"] + f"#page={e['page_start']}"})
            except ValueError as exc:
                response["answer"], response["error"] = None, str(exc)
        row["validation_error_before"] = old_error
        rows.append(row)
    output = {"source": str(LIVE.relative_to(ROOT)), "source_sha256": hashlib.sha256(LIVE.read_bytes()).hexdigest(),
              "validator_code_sha256": pipeline_sha256(), "timestamp_utc": datetime.now(timezone.utc).isoformat(),
              "new_api_calls": 0, "rows": rows}
    VALIDATED.write_text(json.dumps(output, ensure_ascii=False, indent=2))
    print(json.dumps({"rows": len(rows), "new_api_calls": 0, "errors_after_validation": sum(bool(r['response']['error']) for r in rows)}))


def summarize(rows):
    grouped = defaultdict(list)
    for row in rows:
        grouped[(row["suite"], row["method"], "all")].append(row)
        grouped[(row["suite"], row["method"], row["category"])].append(row)
    result = []
    for (suite, method, category), group in sorted(grouped.items()):
        scored = [r for r in group if r["recall_at_5"] is not None]
        result.append({"suite": suite, "method": method, "category": category, "questions": len(group),
                       "gold_questions": len(scored),
                       "mean_recall_at_5": mean(r["recall_at_5"] for r in scored) if scored else None,
                       "all_gold_found": sum(r["all_gold_found"] for r in scored),
                       "mean_latency_ms": mean(r["response"]["latency_ms"] for r in group),
                       "median_latency_ms": median(r["response"]["latency_ms"] for r in group)})
    return result


def retrieve():
    DEST.mkdir(parents=True, exist_ok=True)
    output = DEST / "retrieval.json"
    if output.exists():
        raise SystemExit("retrieval.json đã tồn tại; giữ nguyên phép đo đã chạy")
    engine = Searcher()
    questions = read_jsonl(QUESTIONS)
    source = [("original_30", ROOT/"evaluation/questions.jsonl"),
              ("relations_8", ROOT/"evaluation/questions_multidoc_ocr.jsonl"), ("scoped_20", QUESTIONS)]
    for method in METHODS:
        engine.retrieve(questions[0]["question"], method)
    rows = []
    for suite, path in source:
        for index, q in enumerate(read_jsonl(path)):
            gold = set(q["gold_article_ids"])
            if not gold <= set(engine.by_id): raise ValueError(f"Gold không có trong corpus: {q['question_id']}")
            # Đổi thứ tự đo để không luôn ưu tiên cùng một phương pháp.
            offset = index % len(METHODS)
            for method in METHODS[offset:] + METHODS[:offset]:
                response = answer(q["question"], method, engine, True)
                found = set(response["retrieved_article_ids"])
                assert not response["error"] and response["api_calls"] == 0
                rows.append({"suite": suite, "question_id": q["question_id"], "question": q["question"],
                             "category": q.get("study_group", q["category"]), "gold_answer": q["gold_answer"],
                             "gold_article_ids": q["gold_article_ids"], "answerable": q.get("answerable", bool(gold)), "method": method,
                             "recall_at_5": len(gold & found) / len(gold) if gold else None,
                             "all_gold_found": gold <= found if gold else None, "response": response})
    payload = {"timestamp_utc": datetime.now(timezone.utc).isoformat(), "code_sha256": pipeline_sha256(),
               **index_fingerprint(engine.directory), "config": effective_config(), "runtime_versions": runtime_versions(),
               "question_sha256": {suite: hashlib.sha256(path.read_bytes()).hexdigest() for suite, path in source},
               "summary": summarize(rows), "rows": rows}
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    with (DEST/"retrieval_summary.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(payload["summary"][0]))
        writer.writeheader(); writer.writerows(payload["summary"])
    # Chỉ số mỗi câu, dễ truy từ bảng tới JSON chứa chứng cứ nguyên văn.
    with (DEST/"retrieval_results.csv").open("w", newline="") as f:
        fields = ("suite", "question_id", "method", "category", "answerable", "recall_at_5", "all_gold_found", "latency_ms", "retrieved_ids")
        writer = csv.DictWriter(f, fieldnames=fields); writer.writeheader()
        for row in rows:
            writer.writerow({**{key: row[key] for key in fields if key not in ("latency_ms", "retrieved_ids")},
                             "latency_ms": row["response"]["latency_ms"], "retrieved_ids": ";".join(row["response"]["retrieved_article_ids"])})
    print(json.dumps([r for r in payload["summary"] if r["category"] == "all"], ensure_ascii=False))


def write_report():
    raw = json.loads((DEST/"retrieval.json").read_text())
    questions = read_jsonl(QUESTIONS)
    live = read_jsonl(LIVE) if LIVE.exists() else []
    raw_errors = sum(bool(r["response"]["error"]) for r in live)
    if VALIDATED.exists():
        checked = json.loads(VALIDATED.read_text())
        if checked["source_sha256"] != hashlib.sha256(LIVE.read_bytes()).hexdigest():
            raise ValueError("Tệp revalidation thuộc log API khác")
        live = checked["rows"]
    latest = {}
    for row in live: latest[(row["question_id"], row["method"])] = row["response"]
    paired = [q for q in questions if all((q["question_id"], m) in latest and latest[(q["question_id"], m)]["answer"]
              and not latest[(q["question_id"], m)]["error"] for m in ("rag", "graph_rag"))]
    errors = sum(bool(r["response"]["error"]) for r in live)
    lines = ["# Thực nghiệm RAG và GraphRAG sau sửa lỗi — 01/10/2026", "",
             "## Phạm vi và trạng thái thực nghiệm", "",
             "Đây là phép thử gọn phục vụ nghiên cứu khoa học cấp trường. Không kiểm tra tải lớn; tập trung chất lượng truy xuất, đáp án, dẫn nguồn, từ chối và chi phí quan sát được.", "",
             "Corpus 9 PDF, 449 đoạn; OCR chưa hiệu đính toàn bộ và hiệu lực hiện hành chưa xác minh. Cả hai pipeline dùng cùng corpus, top_k=5, trần 6.500 ký tự chứng cứ, prompt JSON có cấu trúc, temperature=0 và model `gemini-3.5-flash-lite`. "
             "Đoạn dài được embedding bằng cửa sổ 256 token, overlap 64, trung bình vector cửa sổ rồi chuẩn hóa; không đổi ID đoạn/gold.", "",
             "Truy xuất chạy toàn bộ 30 câu cũ, 8 câu quan hệ và 20 câu có phạm vi văn bản rõ hơn, thêm hybrid vector/TF-IDF không graph làm đối chứng. Tổng 174 lượt truy xuất, không gọi Gemini. "
             "Bộ 20 câu chọn trước đáp án mới: 4 một điều, 4 nhiều điều, 4 phiên bản, 4 quan hệ và 4 ngoài corpus. Tám câu S/M thêm phạm vi bản hợp nhất để gold không mơ hồ; chúng không phải câu nguyên trạng trong bộ 30.", "",
             "Bộ câu hỏi/gold kế thừa bộ nội bộ đã có, bộ quan hệ được viết sau đồ thị; chưa có người độc lập soạn/chấm. Vì vậy đây là thí nghiệm thăm dò có công bố thiên lệch, không phải benchmark độc lập.", "",
             f"Gemini: dự kiến 40 lượt/20 cặp; thực tế ghi **{len(live)} lượt**, lỗi trong log gốc **{raw_errors}**, lỗi sau kiểm tra lại **{errors}**, **{len(paired)}/20 cặp** đủ đáp án hợp lệ. Chưa chạy: {40-len(latest)} lượt. Không gộp kết quả trước OCR hoặc model 3.8 Flash vào bảng này.", "",
             "R03 GraphRAG ban đầu bị bộ đọc citation chặn nhóm `[ID1, ID2]` dù cả hai ID hợp lệ. Sau sửa, toàn bộ JSON đã lưu được kiểm tra lại offline, không sửa câu trả lời thô và không gọi thêm API. "
             "Log gốc giữ nguyên; `generation_revalidated.json` ghi hash log gốc, code validator, lỗi trước sửa và 0 request mới. Mọi độ trễ/token bên dưới vẫn là số đo của request gốc.", "",
             "Nhịp request tối thiểu 5 giây (~12/phút). SDK một request/lượt, timeout 30 giây; dừng khi gặp quota/quyền API hoặc hai lỗi 503 liên tiếp. Mức 15 RPM là thông tin người dùng cung cấp; hạn mức thực tế còn phụ thuộc project/model/tier, không suy ra chỉ từ tên model. "
             "[Model chính thức](https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash-lite), [hạn mức API](https://ai.google.dev/gemini-api/docs/rate-limits).", "",
             "## Chỉ số truy xuất", "",
             "Recall@5 theo câu = số gold tìm được / số gold; trung bình chỉ trên câu có gold. All-gold đếm câu tìm đủ mọi gold. Câu ngoài corpus không có Recall; chất lượng từ chối phải đọc đáp án sinh. "
             "Độ trễ là thời gian pipeline sau khi model/index đã nạp, loại thời gian chờ pacing; `wall_ms` và `pacing_wait_ms` lưu riêng. Một lần đo không đủ kết luận độ ổn định hiệu năng.", "",
             "| Bộ câu | Phương pháp | Câu có gold | Recall@5 | Đủ mọi gold | Độ trễ TB (ms) |", "|---|---|---:|---:|---:|---:|"]
    for summary in raw["summary"]:
        if summary["category"] != "all": continue
        lines.append(f"| {summary['suite']} | {LABELS[summary['method']]} | {summary['gold_questions']} | {summary['mean_recall_at_5']:.4f} | {summary['all_gold_found']}/{summary['gold_questions']} | {summary['mean_latency_ms']:.2f} |")
    lines += ["", "Bảng chi tiết theo nhóm ở `retrieval_summary.csv`; từng câu, chứng cứ/trace ở `retrieval_results.csv` và `retrieval.json`.", "",
              "Độ trễ trung vị của original_30: " + "; ".join(f"{LABELS[s['method']]} {s['median_latency_ms']:.2f} ms" for s in raw["summary"] if s["suite"] == "original_30" and s["category"] == "all") + ". "
              "Trung bình có outlier khi đo song song với tiến trình đánh giá Gemini; không dùng bảng này để khẳng định phương pháp nào nhanh hơn ổn định.", ""]
    score_map = {}
    score_path = DEST / "answer_scores.json"
    if score_path.exists():
        scores = json.loads(score_path.read_text())
        if scores["questions_sha256"] != hashlib.sha256(QUESTIONS.read_bytes()).hexdigest() or scores["revalidated_sha256"] != hashlib.sha256(VALIDATED.read_bytes()).hexdigest():
            raise ValueError("Điểm chấm thuộc snapshot đáp án/câu hỏi khác")
        score_map = {(r["question_id"], r["method"]): r for r in scores["rows"]}
        if set(score_map) != {(q["question_id"], m) for q in paired for m in ("rag", "graph_rag")}:
            raise ValueError("Phiếu chấm không khớp tập cặp hợp lệ")
        lines += ["## Đánh giá sơ bộ nội dung đáp án", "",
                  "**Người/chương trình đánh giá:** " + scores["assessor"] + ". Điểm do trợ lý đối chiếu từng đáp án với gold và chứng cứ, không dùng bộ dò từ khóa. "
                  "Chưa có người phản biện độc lập; đây là nguồn ghi chép để người làm nghiên cứu kiểm tra, không trình bày như kết quả chấm bởi hội đồng.", "",
                  *[f"- **{metric}:** {description}" for metric, description in scores["rubric"].items()], "",
                  "| Thước đo | RAG vector | GraphRAG |", "|---|---:|---:|"]
        for metric, label in (("correct", "Đúng ý chính/phạm vi"), ("complete", "Đủ ý theo gold"), ("citation_support", "Nguồn hỗ trợ phát biểu"), ("appropriate_refusal", "Từ chối đúng câu ngoài corpus")):
            counts = []
            for method in ("rag", "graph_rag"):
                measured = [r[metric] for r in scores["rows"] if r["method"] == method and r[metric] is not None]
                counts.append(f"{sum(measured)}/{len(measured)}")
            lines.append(f"| {label} | {counts[0]} | {counts[1]} |")
        for metric, label in (("mean", "Độ trễ TB pipeline (ms)"), ("median", "Độ trễ trung vị pipeline (ms)")):
            fn = mean if metric == "mean" else median
            vals = [fn(latest[(q["question_id"], m)]["latency_ms"] for q in paired) for m in ("rag", "graph_rag")]
            lines.append(f"| {label} | {vals[0]:.2f} | {vals[1]:.2f} |")
        for key, label in (("input", "Token vào tổng"), ("output", "Token ra tổng"), ("total", "Token tổng")):
            vals = [sum(latest[(q["question_id"], m)]["token_usage"][key] or 0 for q in paired) for m in ("rag", "graph_rag")]
            lines.append(f"| {label} | {vals[0]} | {vals[1]} |")
        wins = losses = ties = 0
        for q in paired:
            a = score_map[(q["question_id"], "rag")]["correct"]
            b = score_map[(q["question_id"], "graph_rag")]["correct"]
            if a is None: continue
            wins += b > a; losses += a > b; ties += a == b
        n = wins + losses
        p_value = min(1, 2 * sum(math.comb(n, i) for i in range(min(wins, losses)+1)) / 2**n) if n else 1
        lines += ["", f"Trên 16 câu trả lời được: GraphRAG đúng hơn ở {wins} câu, RAG đúng hơn ở {losses} câu, {ties} câu bằng nhau theo thước đo đúng nội dung. "
                  f"Kiểm định nhị thức hai phía trên {n} cặp bất đồng (McNemar exact) cho p={p_value:.4f}; không có bằng chứng đủ mạnh ở mức 0,05 về ưu thế chung. "
                  "Đây chỉ là phép kiểm tra thăm dò trên bộ chọn có thiên lệch, không loại bỏ hạn chế thiết kế mẫu.", "",
                  "| Nhóm | Số câu | RAG đúng / đủ / nguồn | GraphRAG đúng / đủ / nguồn |", "|---|---:|---|---|"]
        for group in ("mot_dieu", "nhieu_dieu", "phien_ban", "quan_he"):
            text = []
            for method in ("rag", "graph_rag"):
                entries = [r for r in scores["rows"] if r["method"] == method and r["group"] == group]
                text.append(" / ".join(f"{sum(r[k] for r in entries)}/{len(entries)}" for k in ("correct", "complete", "citation_support")))
            lines.append(f"| {group} | 4 | {text[0]} | {text[1]} |")
        lines += ["", "Không quy token thấp hơn thành ưu thế hiệu quả nếu hệ thống từ chối nhiều câu trả lời được. Số token trên là tổng 20 lượt/phương pháp, gồm bốn từ chối đúng ngoài corpus và các từ chối sai. Không ước tính chi phí tiền.", "",
                  "Gold S02 yêu cầu học phí/điều kiện, gold V05 chỉ yêu cầu tuần rút; đây là sự không đồng nhất của độ đầy đủ trong bộ nội bộ. Hai phương pháp vẫn được chấm cùng gold ở từng câu, nhưng cần thống nhất rubric khi thiết kế bộ độc lập.", ""]
        with (DEST/"answer_results.csv").open("w", newline="") as f:
            fields = ("question_id", "method", "group", "correct", "complete", "citation_support", "appropriate_refusal", "note")
            writer = csv.DictWriter(f, fieldnames=fields); writer.writeheader()
            writer.writerows(scores["rows"])
    lines += ["## Phân tích nguyên nhân và ví dụ đối chiếu", "",
              "### Truy xuất", "",
              "- Bộ 30 câu nguyên trạng: RAG 0,74, GraphRAG 0,78, hybrid không graph 0,72. RAG tìm đủ gold 17/25, GraphRAG 16/25. Lợi ích của GraphRAG tập trung ở phiên bản (1,00 so với RAG/hybrid 0,60); câu một điều RAG 0,9167 cao hơn GraphRAG/hybrid 0,8333. Câu nhiều điều cả RAG/GraphRAG 0,5625, hybrid 0,6250.",
              "- Bộ 8 quan hệ: RAG 0,25, hybrid 0,625, GraphRAG 1,00. TF-IDF đã giúp đáng kể; phần tăng từ hybrid tới GraphRAG phù hợp với việc thêm cạnh/chứng cứ được ưu tiên. Đây chưa là tách riêng mọi hiệu ứng của graph vì hai thuật toán còn khác tập ứng viên và điểm thưởng cạnh.",
              "- Bộ 20 có phạm vi rõ: GraphRAG 0,78125, RAG 0,625, hybrid 0,59375. So với bộ 30, khác cả phân bố nhóm và wording, nên không dùng chênh lệch này để chứng minh tác động nhân quả của sửa code.", "",
              "### Ví dụ GraphRAG hỗ trợ tốt hơn", "",
              "1. V02: tìm Điều 22 khoản 2 để trả đúng QĐ787/2018; RAG bỏ lỡ và từ chối.",
              "2. R01: cạnh REPLACES đưa vào đoạn trang 1 QĐ721, trả cả QĐ254 và QĐ1432; RAG thiếu chứng cứ và từ chối.",
              "3. R02: tìm đủ trang 1 và 2 của QĐ1077 để trả TT08 và QĐ239; RAG thiếu một phần. R06 tương tự với hai quyết định được TT08 thay thế.", "",
              "### Ví dụ RAG tốt hơn hoặc hai phương pháp ngang nhau", "",
              "1. S07: RAG tìm khoảng A=8,5–10/F<4 ở bản hợp nhất; GraphRAG dùng quy đổi A=4/F=0 của TT08. ID dẫn có thật nhưng sai trọng tâm/phạm vi. Đây là lỗi chọn/sinh nội dung, không phải lỗi ID giả.",
              "2. M01: RAG trả GPA2,00 và thời hạn ba tháng; GraphRAG từ chối vì thiếu chứng cứ đầy đủ. RAG còn thiếu một số điều kiện so với gold.",
              "3. S06/V04: cả hai trả đủ thông tin và dẫn nguồn đúng; GraphRAG không cải thiện nội dung. U01/U02/U03/U05: cả hai từ chối phù hợp.", "",
              "### Lỗi chung và hướng nghiên cứu", "",
              "- M02: hai phương pháp đều lấy Điều7 khoản3 về 33 tín chỉ trong đợt đăng ký chính, bỏ lỡ khoản5 về khối lượng học kỳ 27 và yêu cầu điều chỉnh. Câu trả lời có nguồn cho 33 nhưng chưa trả mức cuối cùng theo gold. Cần đánh giá sự đầy đủ của chuỗi điều kiện/ngoại lệ, không chỉ xem ID có thật.",
              "- M05/M08: thiếu một phần gold dẫn tới từ chối sai trên câu trả lời được. Với top_k nhỏ, các đoạn cạnh tranh có thể chiếm chỗ của điều khoản cần thiết; trace cho phép phân biệt lỗi truy xuất với lỗi sinh.",
              "- S02/S04/V01: đoạn cần thiết đã được tìm nhưng model lược bỏ học phí/điều kiện hoặc ngoại lệ. Đây là thiếu ý khi sinh, không sửa được chỉ bằng nâng Recall.",
              "- Việc thêm số hiệu vào câu hỏi có thể làm đoạn mở đầu bản hợp nhất xếp cao; cần kiểm tra cơ chế phạm vi văn bản và đa dạng chứng cứ trong thí nghiệm kế tiếp, tránh hard-code theo câu hỏi.",
              "- Token thấp hơn của RAG phần nào đi cùng nhiều từ chối sai hơn; độ trễ một lượt và token không đủ để kết luận chi phí/hiệu năng tổng quát.", "",
              "## Câu hỏi và đáp án Gemini từng trường hợp", "",
              "Đáp án dưới đây là dữ liệu API thật; lỗi/chưa chạy được ghi nguyên trạng. Không tự tạo đáp án thay thế và không chấm điểm nội dung khi không có đáp án hợp lệ.", ""]
    for q in questions:
        lines += [f"### {q['question_id']} — {q['study_group']}", "", q["question"], "", f"**Gold:** {q['gold_answer']}", "",
                  f"**Gold ID:** {', '.join(q['gold_article_ids']) or 'Không có; cần từ chối'}", ""]
        for method in ("rag", "graph_rag"):
            response = latest.get((q["question_id"], method))
            lines += [f"**{LABELS[method]}**", ""]
            if response is None:
                lines += ["Chưa chạy.", ""]; continue
            lines += [*("> " + line for line in (response["answer"] or "Không có đáp án hợp lệ.").splitlines()), "",
                      f"Lỗi: {response['error'] or 'Không'}. Độ trễ: {response['latency_ms']} ms; chờ nhịp: {response['pacing_wait_ms']} ms; API: {response['api_calls']}; token: `{json.dumps(response['token_usage'], ensure_ascii=False)}`.", "",
                      "ID truy xuất: " + ", ".join(response["retrieved_article_ids"]), "",
                      "Nguồn dẫn: " + (", ".join(f"[{c['article_id']}]({c['url']})" for c in response["citations"]) or "Không có"), ""]
            score = score_map.get((q["question_id"], method))
            if score:
                if score["correct"] is None:
                    lines += [f"**Từ chối phù hợp:** {score['appropriate_refusal']}/1. {score['note']}", ""]
                else:
                    total = sum(score[k] for k in ("correct", "complete", "citation_support"))
                    lines += [f"**Đối chiếu sơ bộ: {total}/3** (đúng {score['correct']}, đủ {score['complete']}, nguồn {score['citation_support']}). {score['note']}", ""]
    lines += ["## Chấm nội dung và giới hạn", "",
              "Thang dự kiến: đúng nội dung 0/1, đủ ý/điều kiện 0/1, citation hỗ trợ nội dung 0/1; câu ngoài corpus chấm từ chối phù hợp 0/1 riêng. Chỉ so sánh trên cặp đủ hai đáp án. "
              "Citation hợp lệ về ID không đồng nghĩa đúng nội dung. Phiếu chấm cần ghi người/chương trình đánh giá và lý do đối chiếu chứng cứ.", "",
              f"Phiên này có {len(paired)} cặp hợp lệ sau kiểm tra lại; điểm và token dùng đúng các cặp này. Log gốc lưu riêng lỗi validation local, không có lỗi dịch vụ/quota trong 40 request của bộ chính. "
              "Trong các lần chạy khác, phải loại riêng lỗi dịch vụ khỏi đánh giá nội dung; không coi 503 là bằng chứng một cách truy xuất trả lời sai hơn.", "",
              "## Tái lập", "", "```bash", "HF_HUB_OFFLINE=1 python3 -m unittest discover -s tests -v",
              "python3 -m evaluation.research_study report", "```", "",
              "Metadata khóa hash corpus/vector/graph/câu hỏi/code/model hiệu dụng và phiên bản thư viện. Khi đổi code/model/corpus, tạo run mới; không nối vào checkpoint khác phiên bản.", ""]
    (DEST/"BAO_CAO_THUC_NGHIEM.md").write_text("\n".join(lines)+"\n")
    print(f"Report: {len(paired)} complete pairs, {len(live)} API attempts")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("retrieve", "revalidate", "report"))
    args = parser.parse_args()
    if args.command == "retrieve": retrieve()
    elif args.command == "revalidate": revalidate()
    else: write_report()
