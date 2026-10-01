"""Đo truy xuất trên câu hỏi về quan hệ giữa các văn bản OCR; không gọi Gemini."""
from __future__ import annotations

import json
import hashlib
from collections import defaultdict
from datetime import datetime, timezone
from statistics import mean, median

from src.project import ROOT, Searcher, answer, pipeline_sha256, read_jsonl, effective_config, index_fingerprint, runtime_versions

QUESTIONS = ROOT / "evaluation/questions_multidoc_ocr.jsonl"


def main() -> None:
    questions = read_jsonl(QUESTIONS)
    if len({question["question_id"] for question in questions}) != len(questions):
        raise ValueError("ID câu hỏi bị trùng")
    searcher = Searcher()
    corpus_ids = set(searcher.by_id)
    if questions:
        searcher.retrieve(questions[0]["question"], "rag")
        searcher.retrieve(questions[0]["question"], "graph_rag")
    rows = []
    for question in questions:
        gold = set(question["gold_article_ids"])
        if not gold or not gold <= corpus_ids:
            raise ValueError(f"Gold ID không có trong corpus: {question['question_id']}")
        for method in ("rag", "graph_rag"):
            result = answer(question["question"], method, searcher, retrieve_only=True)
            found = set(result["retrieved_article_ids"])
            rows.append({"question_id": question["question_id"], "category": question["category"],
                         "method": method, "question": question["question"],
                         "gold_answer": question["gold_answer"], "gold_article_ids": sorted(gold),
                         "retrieved_article_ids": result["retrieved_article_ids"],
                         "found_gold_ids": sorted(gold & found),
                         "recall_at_5": len(gold & found) / len(gold),
                         "all_gold_found": gold <= found,
                         "latency_ms": result["latency_ms"], "trace": result["retrieval_trace"]})
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["method"]].append(row)
    summary = {method: {"questions": len(group),
                        "mean_recall_at_5": round(mean(row["recall_at_5"] for row in group), 4),
                        "all_gold_found": sum(row["all_gold_found"] for row in group),
                        "median_latency_ms": round(median(row["latency_ms"] for row in group), 2)}
               for method, group in grouped.items()}
    output = {"timestamp_utc": datetime.now(timezone.utc).isoformat(),
              "mode": "retrieve_only", "questions_file": str(QUESTIONS.relative_to(ROOT)),
              "questions_sha256": hashlib.sha256(QUESTIONS.read_bytes()).hexdigest(),
              **index_fingerprint(searcher.directory), "runtime_versions": runtime_versions(),
              "code_sha256": pipeline_sha256(),
              "corpus_chunks": len(corpus_ids), "config": effective_config(),
              "summary": summary, "rows": rows}
    destination = ROOT / "evaluation/runs" / ("multidoc_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f") + ".json")
    destination.write_text(json.dumps(output, ensure_ascii=False, indent=2))
    print(json.dumps({"output": str(destination), "summary": summary}, ensure_ascii=False))


if __name__ == "__main__":
    main()
