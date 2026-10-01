"""Kiểm tra snapshot hiện tại; không ghi đè kết quả nghiên cứu cũ.

Chạy: HF_HUB_OFFLINE=1 python3 -m evaluation.review_20261001
Các lượt Gemini trong script này đều giả lập; live API chạy riêng.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
import sys
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from types import SimpleNamespace
from unittest.mock import patch

import networkx as nx
import numpy as np
from fastapi.testclient import TestClient

import server
from src import project as p
from src.legal_graph import reviewed_relations
from src.ocr_corpus import build_ocr_articles

OUT = p.ROOT / "evaluation/runs/review_20261001"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    checks = []
    def check(name, condition, **details):
        checks.append({"name": name, "passed": bool(condition), **details})
        print(f"{'PASS' if condition else 'FAIL'} {name}", flush=True)

    rows = p.read_jsonl(p.ARTICLES)
    ids = {r["id"] for r in rows}
    vectors = np.load(p.VECTORS)
    graph = nx.node_link_graph(json.loads(p.GRAPH.read_text()), edges="links")
    check("corpus_vector_integrity", len(ids) == len(rows) == len(vectors)
          and np.isfinite(vectors).all() and np.allclose(np.linalg.norm(vectors, axis=1), 1, atol=1e-5),
          documents=len({r["document_id"] for r in rows}), chunks=len(rows), vector_shape=list(vectors.shape),
          graph_nodes=graph.number_of_nodes(), graph_edges=graph.number_of_edges())
    with (p.ROOT / "data/source_manifest.csv").open() as f:
        manifest = list(csv.DictReader(f))
    check("manifest_hashes", all(hashlib.sha256((p.ROOT/r["local_path"]).read_bytes()).hexdigest() == r["sha256"]
                                 for r in manifest if r["local_path"]))
    ocr = build_ocr_articles(p.ROOT)
    check("ocr_rebuild_matches", ocr == [r for r in rows if r.get("extraction_method") == "user_supplied_ocr"], chunks=len(ocr))
    relations = reviewed_relations(p.ROOT, rows)
    check("legal_evidence_integrity", all(set(e["evidence_article_ids"]) <= ids for e in relations), relations=len(relations))

    engine = p.Searcher()
    p.answer("Sinh viên được rút học phần vào tuần nào?", "rag", engine, True)
    measured = []
    for file in ("questions.jsonl", "questions_multidoc_ocr.jsonl"):
        questions = p.read_jsonl(p.ROOT / "evaluation" / file)
        check(f"gold_integrity_{file}", len({q["question_id"] for q in questions}) == len(questions)
              and all(set(q["gold_article_ids"]) <= ids for q in questions),
              categories=dict(Counter(q["category"] for q in questions)))
        for q in questions:
            for method in ("rag", "graph_rag"):
                r = p.answer(q["question"], method, engine, True)
                gold = set(q["gold_article_ids"])
                found = set(r["retrieved_article_ids"])
                assert found <= ids and len(found) <= p.CONFIG["top_k"]
                assert sum(len(e["text"]) for e in r["evidence"]) <= p.CONFIG["max_evidence_chars"]
                assert r["api_calls"] == 0 and r["answer"] is None and r["error"] is None
                measured.append({"file": file, "question_id": q["question_id"], "question": q["question"],
                                 "method": method, "recall": len(gold & found)/len(gold) if gold else None,
                                 "all_gold": gold <= found if gold else None, "response": r})
    summaries = []
    for file in ("questions.jsonl", "questions_multidoc_ocr.jsonl"):
        for method in ("rag", "graph_rag"):
            group = [r for r in measured if r["file"] == file and r["method"] == method]
            scored = [r for r in group if r["recall"] is not None]
            summaries.append({"file": file, "method": method, "questions": len(group), "gold_questions": len(scored),
                              "mean_recall": mean(r["recall"] for r in scored),
                              "all_gold": sum(r["all_gold"] for r in scored),
                              "mean_latency_ms": mean(r["response"]["latency_ms"] for r in group)})
    check("retrieval_76_calls", len(measured) == 76, summary=summaries)

    with patch.object(server, "searcher", return_value=engine):
        client = TestClient(server.app)
        check("api_health_suggestions_static", client.get("/api/health").status_code == 200
              and len(client.get("/api/suggestions").json()) == 6 and client.get("/").status_code == 200)
        for mode in ("rag", "graph_rag", "compare"):
            reply = client.post("/api/chat", json={"question": "QĐ 721/2024 thay thế văn bản nào?", "mode": mode, "retrieve_only": True})
            check(f"api_retrieve_{mode}", reply.status_code == 200 and all(r["api_calls"] == 0 for r in reply.json()["results"].values()))
        check("api_validation", all(client.post("/api/chat", json={"question": q}).status_code == 422 for q in ("a", "   ", "x"*2001)))
        with patch.dict(os.environ, {"GEMINI_API_KEY": ""}):
            reply = client.post("/api/chat", json={"question": "Sinh viên rút học phần khi nào?"}).json()
            check("api_missing_key", all(r["api_calls"] == 0 and r["error"] for r in reply["results"].values()))
        for code in (503, 429):
            with patch("google.genai.Client", side_effect=RuntimeError(f"provider {code}")), patch.object(server, "wait_for_gemini_slot"):
                result = client.post("/api/chat", json={"question": "Sinh viên rút học phần khi nào?"}).json()["results"]
                check(f"api_compare_skip_{code}", result["rag"]["api_calls"] == 1 and result["graph_rag"]["api_calls"] == 0 and str(code) in result["rag"]["error"])

    evidence = measured[0]["response"]["evidence"]
    stub = SimpleNamespace(retrieve=lambda *args: (evidence, {}))
    def generated(text):
        fake = SimpleNamespace(models=SimpleNamespace(generate_content=lambda **kw: SimpleNamespace(text=text, usage_metadata=None)))
        with patch("google.genai.Client", return_value=fake):
            return p.answer("kiểm tra nguồn", "rag", stub)
    check("invalid_citation_blocked", generated("Sai [FAKE-ID]")["answer"] is None)
    check("valid_citation_allowed", generated(f"Đúng [{evidence[0]['id']}]")["error"] is None)
    check("refusal_allowed", generated("Chưa xác định được từ tập tài liệu.")["error"] is None)
    bypass = generated("Chưa xác định được từ tập tài liệu. Tuy nhiên, sinh viên được nghỉ học 100 ngày không cần xin phép.")
    check("refusal_phrase_blocks_unsupported_claim", bypass["answer"] is None, observed=bypass)
    empty = generated(None)
    check("empty_generation_error", bool(empty["error"]))

    tokenizer = engine.encoder[0]
    lengths = [len(tokenizer(r["text"], truncation=False)["input_ids"]) for r in rows]
    check("embedding_no_silent_truncation", all(n <= 256 for n in lengths), truncated_chunks=sum(n > 256 for n in lengths), max_tokens=max(lengths))

    # Chứng minh checkpoint hiện cho phép tiếp tục khi đổi GEMINI_MODEL.
    from evaluation import run_gemini as runner
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        (root/"evaluation/runs").mkdir(parents=True)
        shutil.copy(p.ROOT/"evaluation/questions.jsonl", root/"evaluation/questions.jsonl")
        with patch.object(runner, "ROOT", root), patch.object(runner, "PACE", root/"evaluation/runs/pace.json"), patch.object(runner, "Searcher", return_value=engine):
            with patch.object(sys, "argv", ["run_gemini", "--run-id", "modelcheck", "--ids", "S01", "--max-new-calls", "0"]):
                with patch.dict(os.environ, {"GEMINI_MODEL": "model-A"}): runner.main()
                with patch.dict(os.environ, {"GEMINI_MODEL": "model-B"}):
                    try:
                        runner.main()
                        blocked = False
                    except SystemExit:
                        blocked = True
        check("checkpoint_blocks_model_change", blocked)

    # Dựng chỉ mục ở bản sao: không làm thay đổi corpus gốc.
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        shutil.copytree(p.ROOT/"data", root/"data")
        with patch.multiple(p, ROOT=root, ARTICLES=root/"data/processed/articles.jsonl", VECTORS=root/"data/processed/vectors.npy", GRAPH=root/"data/processed/graph.json"):
            p.prepare()
            check("prepare_reproduces_corpus", p.read_jsonl(p.ARTICLES) == rows)
            rebuilt_vectors = np.load(p.VECTORS)
            check("prepare_reproduces_vectors", np.allclose(vectors, rebuilt_vectors, atol=1e-5), max_difference=float(np.max(np.abs(vectors-rebuilt_vectors))))
            rebuilt_graph = json.loads(p.GRAPH.read_text())
            check("prepare_reproduces_graph", rebuilt_graph == json.loads((OUT.parents[2]/"data/processed/graph.json").read_text()))
            before = p.ARTICLES.read_bytes()
            with patch.object(p, "build_ocr_articles", side_effect=ValueError("simulated bad OCR")):
                try: p.prepare()
                except ValueError: pass
            check("failed_prepare_preserves_index", p.ARTICLES.read_bytes() == before,
                  chunks_after_failure=len(p.read_jsonl(p.ARTICLES)))
    output = {"timestamp_utc": datetime.now(timezone.utc).isoformat(), "code_sha256": p.pipeline_sha256(),
              "checks": checks, "retrieval_summary": summaries, "retrieval_rows": measured}
    (OUT/"checks.json").write_text(json.dumps(output, ensure_ascii=False, indent=2))
    print(json.dumps({"passed": sum(c["passed"] for c in checks), "total": len(checks), "output": str(OUT/"checks.json")}, ensure_ascii=False))


if __name__ == "__main__":
    # Mọi nhánh sinh ở bộ kiểm tra đều được mock, không dùng key thật.
    with patch.dict(os.environ, {"GEMINI_API_KEY": "review-placeholder-not-a-real-key"}):
        main()
