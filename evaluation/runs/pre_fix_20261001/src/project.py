"""CLI tái tạo corpus, hai cách truy xuất và phép đo truy xuất."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import fitz
import networkx as nx
import numpy as np
import torch
from dotenv import load_dotenv
from sklearn.feature_extraction.text import TfidfVectorizer
from transformers import AutoModel, AutoTokenizer

from src.legal_graph import build_legal_graph, mentioned_documents, relation_intents, reviewed_relations
from src.ocr_corpus import build_ocr_articles

ROOT = Path(__file__).resolve().parents[1]
ARTICLES = ROOT / "data/processed/articles.jsonl"
VECTORS = ROOT / "data/processed/vectors.npy"
GRAPH = ROOT / "data/processed/graph.json"
CONFIG = json.loads((ROOT / "config.json").read_text())
load_dotenv(ROOT / ".env")
TOPICS = {
    "tốt nghiệp": ["tốt nghiệp", "cấp bằng", "văn bằng"],
    "thi và kiểm tra": ["thi", "kiểm tra", "phúc khảo"],
    "điểm": ["điểm", "xếp loại", "đánh giá"],
    "học phần": ["học phần", "tín chỉ", "đăng ký học"],
    "thời gian": ["thời gian", "học kỳ", "khóa học"],
    "chuyển đổi": ["chuyển đổi", "công nhận", "chuyển ngành"],
    "kỷ luật": ["kỷ luật", "buộc thôi học", "cảnh báo"],
}
AUDIENCES = {"chính quy": "chính quy", "vừa làm vừa học": "vừa làm vừa học"}


def pipeline_sha256() -> str:
    digest = hashlib.sha256()
    for path in (ROOT / "src/project.py", ROOT / "src/ocr_corpus.py", ROOT / "src/legal_graph.py"):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))


def build_articles() -> list[dict]:
    """Tách theo tiêu đề Điều; giữ trang đầu/cuối và SHA của PDF gốc."""
    source = ROOT / "data/raw/quyche_hop_nhat_2023.pdf"
    pdf = fitz.open(source)
    sha = hashlib.sha256(source.read_bytes()).hexdigest()
    pieces = []
    for page_no, page in enumerate(pdf, 1):
        text = page.get_text(sort=True)
        for line in text.splitlines(keepends=True):
            pieces.append((page_no, line))
    full_text = "".join(line for _, line in pieces)
    starts = [m.start() for m in re.finditer(r"(?m)^\s*Điều\s+(\d+)\s*\.", full_text)]
    if len(starts) < 20:
        raise ValueError(f"Chỉ nhận diện {len(starts)} điều; kiểm tra PDF gốc")
    offsets = []
    cursor = 0
    for page_no, line in pieces:
        offsets.append((cursor, page_no))
        cursor += len(line)

    def page_at(offset: int) -> int:
        return max(p for start, p in offsets if start <= offset)

    rows = []
    preface = full_text[:starts[0]].strip()
    if preface:
        rows.append({"id": "QC2023-P001-PREFACE", "document_id": "QC2023",
                     "article_id": None, "article_number": None, "clause": None,
                     "title": "Quy chế đào tạo trình độ đại học tại HaUI (hợp nhất QĐ 744/2021 và 666/2023)",
                     "document_number": "744/QĐ-ĐHCN; 666/QĐ-ĐHCN", "text": preface,
                     "page_start": 1, "page_end": page_at(starts[0] - 1),
                     "source_url": "https://sict.haui.edu.vn/media/29/uffile-upload-no-title29811.pdf",
                     "landing_url": "https://sict.haui.edu.vn/vn/html/quy-che",
                     "source_sha256": sha, "source_char_start": 0, "validity": "unknown"})
    for idx, start in enumerate(starts):
        end = starts[idx + 1] if idx + 1 < len(starts) else len(full_text)
        block = full_text[start:end]
        article_no = int(re.search(r"Điều\s+(\d+)", block).group(1))
        # Đoạn theo khoản được ưu tiên; đoạn dài được cắt theo giới hạn ký tự.
        clauses = list(re.finditer(r"(?m)^\s*(\d+)\.\s+", block))
        spans = [(0, clauses[0].start())] if clauses and clauses[0].start() else []
        spans += [(m.start(), clauses[i + 1].start() if i + 1 < len(clauses) else len(block)) for i, m in enumerate(clauses)]
        if not spans:
            spans = [(0, len(block))]
        for clause_idx, (a, b) in enumerate(spans):
            segment = block[a:b].strip()
            if len(segment) < 30:
                continue
            # Cắt tại khoảng trắng để không làm hỏng từ ở ranh giới đoạn.
            chunks = []
            rest = segment
            while len(rest) > 1100:
                cut = rest.rfind(" ", 0, 1100)
                if cut < 700:
                    cut = 1100
                chunks.append(rest[:cut].strip())
                rest = rest[cut:].lstrip()
            if rest.strip():
                chunks.append(rest.strip())
            for part_idx, chunk in enumerate(chunks, 1):
                segment_start = full_text.find(chunk, start, end)
                if segment_start < 0:
                    raise ValueError("Không đối chiếu được đoạn với PDF gốc")
                label = re.match(r"(\d+)\.", segment)
                clause = label.group(1) if label else "title"
                row_id = f"QC2023-D{article_no:02d}-K{clause}-P{part_idx:02d}"
                rows.append({"id": row_id, "document_id": "QC2023", "article_id": f"D{article_no:02d}",
                             "article_number": article_no, "clause": clause, "title": "Quy chế đào tạo trình độ đại học tại HaUI (hợp nhất QĐ 744/2021 và 666/2023)",
                             "document_number": "744/QĐ-ĐHCN; 666/QĐ-ĐHCN", "text": chunk.strip(),
                             "page_start": page_at(segment_start), "page_end": page_at(min(end - 1, segment_start + len(chunk))),
                             "source_url": "https://sict.haui.edu.vn/media/29/uffile-upload-no-title29811.pdf",
                             "landing_url": "https://sict.haui.edu.vn/vn/html/quy-che",
                             "source_sha256": sha, "source_char_start": segment_start,
                             "validity": "unknown"})
    if len({x["id"] for x in rows}) != len(rows):
        raise ValueError("ID điều khoản bị trùng")
    write_jsonl(ARTICLES, rows)
    return rows


def model_encoder():
    name = os.getenv("EMBEDDING_MODEL", CONFIG["embedding_model"])
    revision = CONFIG["embedding_revision"]
    tokenizer = AutoTokenizer.from_pretrained(name, revision=revision)
    model = AutoModel.from_pretrained(name, revision=revision).eval()
    return tokenizer, model


def encode(texts: list[str], encoder=None) -> np.ndarray:
    tokenizer, model = encoder or model_encoder()
    vectors = []
    with torch.inference_mode():
        for i in range(0, len(texts), 16):
            batch = tokenizer(texts[i:i + 16], padding=True, truncation=True, max_length=256, return_tensors="pt")
            output = model(**batch).last_hidden_state
            mask = batch["attention_mask"].unsqueeze(-1)
            pooled = (output * mask).sum(1) / mask.sum(1).clamp(min=1)
            pooled = torch.nn.functional.normalize(pooled, p=2, dim=1)
            vectors.append(pooled.numpy())
    return np.vstack(vectors)


def build_graph(rows: list[dict]) -> nx.Graph:
    relations = reviewed_relations(ROOT, rows)
    (ROOT / "data/processed/legal_relations.json").write_text(
        json.dumps(relations, ensure_ascii=False, indent=2))
    return build_legal_graph(rows, relations, TOPICS, AUDIENCES)


def prepare() -> None:
    started = time.perf_counter()
    rows = build_articles() + build_ocr_articles(ROOT)
    if len({row["id"] for row in rows}) != len(rows):
        raise ValueError("ID đoạn corpus bị trùng")
    write_jsonl(ARTICLES, rows)
    parsed = time.perf_counter()
    vectors = encode([r["text"] for r in rows])
    np.save(VECTORS, vectors)
    embedded = time.perf_counter()
    graph = build_graph(rows)
    data = nx.node_link_data(graph, edges="links")
    GRAPH.write_text(json.dumps(data, ensure_ascii=False))
    finished = time.perf_counter()
    metadata = {"timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "parse_ms": round((parsed - started) * 1000, 2),
                "vector_index_ms": round((embedded - parsed) * 1000, 2),
                "graph_index_ms": round((finished - embedded) * 1000, 2),
                "total_ms": round((finished - started) * 1000, 2)}
    (ROOT / "data/processed/build_meta.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2))
    print(json.dumps({"documents": len(set(r["document_id"] for r in rows)),
                      "articles": len(set(r["article_id"] for r in rows if r["article_id"])),
                      "chunks": len(rows), "vector_dimensions": vectors.shape[1],
                      "graph_nodes": graph.number_of_nodes(), "graph_edges": graph.number_of_edges(),
                      "build_timing_ms": metadata}, ensure_ascii=False))


class Searcher:
    def __init__(self):
        self.rows = read_jsonl(ARTICLES)
        self.by_id = {r["id"]: r for r in self.rows}
        self.vectors = np.load(VECTORS)
        self.encoder = model_encoder()
        self.graph = nx.node_link_graph(json.loads(GRAPH.read_text()), edges="links")
        self.lexical = TfidfVectorizer(analyzer="char", ngram_range=(2, 4), min_df=1)
        self.lexical_matrix = self.lexical.fit_transform([r["text"] for r in self.rows])

    def retrieve(self, question: str, method: str, k: int | None = None):
        k = k or CONFIG["top_k"]
        if method == "rag":
            query = encode([question], self.encoder)[0]
            scores = self.vectors @ query
            ranks = np.argsort(-scores)[:k]
            trace = {"method": "vector_cosine", "top_k": k, "candidates": [{"id": self.rows[i]["id"], "score": round(float(scores[i]), 4)} for i in ranks]}
        elif method == "graph_rag":
            query = encode([question], self.encoder)[0]
            semantic_scores = self.vectors @ query
            lexical_scores = (self.lexical_matrix @ self.lexical.transform([question]).T).toarray().ravel()
            seeds = list(dict.fromkeys([*np.argsort(-lexical_scores)[:3], *np.argsort(-semantic_scores)[:2]]))
            topic_nodes = ["Topic:" + topic for topic, terms in TOPICS.items() if any(t in question.lower() for t in terms)]
            candidate_ids = {self.rows[i]["id"] for i in seeds}
            traversed = []
            related_documents = set()
            for node in topic_nodes:
                if node in self.graph:
                    for source, _, data in self.graph.in_edges(node, data=True):
                        if data.get("relation") == "ABOUT":
                            candidate_ids.add(source.removeprefix("Article:"))
            for i in seeds:
                chunk = "Article:" + self.rows[i]["id"]
                document = "Document:" + self.rows[i]["document_id"]
                for source, _, data in self.graph.in_edges(chunk, data=True):
                    if data.get("relation") == "NEXT":
                        candidate_ids.add(source.removeprefix("Article:"))
                for _, target, data in self.graph.out_edges(chunk, data=True):
                    if data.get("relation") == "NEXT":
                        candidate_ids.add(target.removeprefix("Article:"))
                frontier = {document}
                visited = {document}
                for _ in range(2):
                    following = set()
                    for current in frontier:
                        for source, target, data in [*self.graph.in_edges(current, data=True),
                                                     *self.graph.out_edges(current, data=True)]:
                            if data.get("relation") not in ("AMENDS", "REPLACES", "SUPPLEMENTS", "CONSOLIDATES", "CITES"):
                                continue
                            other = source if target == current else target
                            traversed.append({"from": source, "to": target, "relation": data["relation"],
                                              "evidence_article_ids": data["evidence_article_ids"],
                                              "evidence_url": data["evidence_url"]})
                            if other not in visited:
                                following.add(other)
                                if self.graph.nodes[other].get("corpus_present"):
                                    related_documents.add(other.removeprefix("Document:"))
                    visited.update(following)
                    frontier = following
            combined = 0.55 * lexical_scores + 0.45 * semantic_scores
            for document_id in related_documents:
                document_indices = [i for i, row in enumerate(self.rows) if row["document_id"] == document_id]
                candidate_ids.update(self.rows[i]["id"] for i in
                                     sorted(document_indices, key=lambda i: -combined[i])[:3])
            # Với câu hỏi quan hệ pháp lý, ưu tiên chính đoạn được ghi làm chứng cứ
            # cho cạnh đã kiểm tra, thay vì chỉ xếp hạng gần nghĩa theo từ khóa.
            matched_documents = mentioned_documents(question, self.graph)
            intents = relation_intents(question)
            relation_evidence_ids = set()
            for document in matched_documents:
                for source, target, data in [*self.graph.in_edges(document, data=True),
                                             *self.graph.out_edges(document, data=True)]:
                    if data.get("relation") in intents and data.get("review_status") == "ocr_page_and_chunk_verified":
                        relation_evidence_ids.update(data["evidence_article_ids"])
                        traversed.append({"from": source, "to": target, "relation": data["relation"],
                                          "evidence_article_ids": data["evidence_article_ids"],
                                          "evidence_url": data["evidence_url"]})
            candidate_ids.update(relation_evidence_ids)
            candidates = [i for i, row in enumerate(self.rows) if row["id"] in candidate_ids]
            ranks = sorted(candidates, key=lambda i: (-(combined[i] + (0.7 if self.rows[i]["id"] in relation_evidence_ids else 0)),
                                                       self.rows[i]["id"]))[:k]
            trace = {"method": "graph_legal_hybrid", "top_k": k,
                     "seed_ids": [self.rows[i]["id"] for i in seeds], "matched_topics": topic_nodes,
                     "matched_documents": sorted(matched_documents),
                     "relation_evidence_ids": sorted(relation_evidence_ids),
                     "related_documents": sorted(related_documents),
                     "traversed_edges": list({(e["from"], e["to"], e["relation"]): e for e in traversed}.values())[:100],
                     "candidate_count": len(candidates),
                     "candidates": [{"id": self.rows[i]["id"],
                                     "score": round(float(combined[i] + (0.7 if self.rows[i]["id"] in relation_evidence_ids else 0)), 4)}
                                    for i in ranks]}
        else:
            raise ValueError("method phải là rag hoặc graph_rag")
        selected = [self.rows[i] for i in ranks]
        # Cùng giới hạn context cho cả hai pipeline.
        budget = CONFIG["max_evidence_chars"]
        evidence = []
        for row in selected:
            if budget <= 0:
                break
            copied = dict(row)
            copied["text"] = copied["text"][:budget]
            budget -= len(copied["text"])
            evidence.append(copied)
        return evidence, trace


def answer(question: str, method: str, searcher: Searcher, retrieve_only: bool = False) -> dict:
    start = time.perf_counter()
    evidence, trace = searcher.retrieve(question, method)
    ids = [r["id"] for r in evidence]
    citations = [{"article_id": r["id"], "label": r["title"] +
                  (f", Điều {r['article_number']}, khoản {r['clause']}" if r.get("article_number") and r.get("clause") not in (None, "title")
                   else f", Điều {r['article_number']}" if r.get("article_number") else "") +
                  f", trang {r['page_start']}" + (" (OCR chưa hiệu đính toàn bộ)" if r.get("extraction_method") == "user_supplied_ocr" else ""),
                  "url": r["source_url"] + f"#page={r['page_start']}"} for r in evidence]
    result = {"question": question, "method": method, "answer": None, "citations": citations,
              "retrieved_article_ids": ids, "evidence": evidence, "retrieval_trace": trace,
              "latency_ms": None, "api_calls": 0, "token_usage": None, "error": None,
              "provider": "gemini" if not retrieve_only else "retrieve_only",
              "model": os.getenv("GEMINI_MODEL", CONFIG["gemini_model"]) if not retrieve_only else None}
    if not retrieve_only:
        key = os.getenv("GEMINI_API_KEY")
        if not key:
            result["error"] = "Thiếu GEMINI_API_KEY; chỉ có kết quả truy xuất."
        elif evidence:
            try:
                from google import genai
                from google.genai import types
                # Mỗi lần answer() chỉ được tạo một request HTTP. Script đánh giá
                # tự điều tiết nhịp; không để SDK thử lại ngầm nếu phiên bản đổi.
                client = genai.Client(api_key=key, http_options=types.HttpOptions(
                    retry_options=types.HttpRetryOptions(attempts=1)))
                prompt = ("Trả lời tiếng Việt dựa DUY NHẤT vào các trích đoạn. Phân biệt số hiệu, phạm vi và phiên bản văn bản; "
                          "không suy đoán hiệu lực hiện hành. Một số đoạn là OCR chưa hiệu đính toàn bộ: "
                          "không khẳng định số liệu/chữ bị nhận dạng mơ hồ. Nếu thiếu chứng cứ, trả lời "
                          "'Chưa xác định được từ tập tài liệu'. Chỉ viện dẫn ID đoạn trong danh sách.\nCâu hỏi: " + question + "\nChứng cứ:\n" +
                          "\n".join(f"[{r['id']}] Văn bản {r['document_id']} ({r.get('document_number') or 'chưa xác định số hiệu'}, "
                                    f"trang {r['page_start']}, hiệu lực hiện hành chưa xác minh; "
                                    f"{'OCR cần đối chiếu' if r.get('extraction_method') == 'user_supplied_ocr' else 'chữ PDF'}): {r['text']}"
                                    for r in evidence))
                response = client.models.generate_content(model=os.getenv("GEMINI_MODEL", CONFIG["gemini_model"]), contents=prompt,
                    config={"temperature": CONFIG["generation_temperature"]})
                result["answer"] = response.text
                result["api_calls"] = 1
                usage = getattr(response, "usage_metadata", None)
                result["token_usage"] = ({"input": getattr(usage, "prompt_token_count", None),
                    "output": getattr(usage, "candidates_token_count", None),
                    "thoughts": getattr(usage, "thoughts_token_count", None),
                    "total": getattr(usage, "total_token_count", None)} if usage else None)
                # Cả ID đoạn PDF và ID đoạn OCR đều phải xuất hiện trong chứng cứ.
                mentioned_ids = set(re.findall(r"\[([A-Za-z0-9_-]+)\]", response.text or ""))
                cited = [c for c in citations if c["article_id"] in mentioned_ids]
                result["citations"] = cited
                refusal = "chưa xác định được từ tập tài liệu" in (response.text or "").lower()
                if (not cited and not refusal) or not mentioned_ids.issubset(set(ids)):
                    result["answer"] = None
                    result["error"] = "Mô hình không dẫn ID chứng cứ hợp lệ; câu trả lời bị chặn."
            except Exception as exc:
                result["api_calls"] = 1
                detail = str(exc).replace(key, "[REDACTED]")
                if "503" in detail or "UNAVAILABLE" in detail:
                    result["error"] = "Gemini đang tạm quá tải (503). Vui lòng thử lại sau."
                elif "429" in detail or "RESOURCE_EXHAUSTED" in detail:
                    result["error"] = "Gemini đã chạm hạn mức (429). Vui lòng thử lại khi hạn mức được khôi phục."
                else:
                    result["error"] = f"Lỗi Gemini: {type(exc).__name__}: {detail[:1000]}"
        else:
            result["answer"] = "Chưa xác định được từ tập tài liệu."
    result["latency_ms"] = round((time.perf_counter() - start) * 1000, 2)
    assert all(c["article_id"] in ids for c in result["citations"])
    return result


def evaluate(retrieve_only: bool = False, selected_ids: list[str] | None = None) -> None:
    questions = read_jsonl(ROOT / "evaluation/questions.jsonl")
    if selected_ids:
        unknown = set(selected_ids) - {q["question_id"] for q in questions}
        if unknown:
            raise ValueError(f"ID câu hỏi không tồn tại: {sorted(unknown)}")
        questions = [q for q in questions if q["question_id"] in selected_ids]
    searcher = Searcher()
    if questions and retrieve_only:
        # Nạp đường suy luận lần đầu trước khi đo độ trễ truy xuất.
        searcher.retrieve(questions[0]["question"], "rag")
        searcher.retrieve(questions[0]["question"], "graph_rag")
    out = ROOT / "evaluation/runs"
    out.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).isoformat()
    run = {"timestamp_utc": timestamp, "mode": "retrieve_only" if retrieve_only else "generate",
              "config": CONFIG, "code_sha256": pipeline_sha256(),
           "questions_sha256": hashlib.sha256((ROOT / "evaluation/questions.jsonl").read_bytes()).hexdigest(),
           "selected_question_ids": [q["question_id"] for q in questions], "rows": []}
    results = []
    for q in questions:
        paired = {method: answer(q["question"], method, searcher, retrieve_only) for method in ("rag", "graph_rag")}
        run["rows"].append({"question_id": q["question_id"], **paired})
        for method, response in paired.items():
            gold = set(q["gold_article_ids"])
            found = set(response["retrieved_article_ids"])
            results.append({"question_id": q["question_id"], "category": q["category"], "method": method,
                            "answerable": q["answerable"], "gold_count": len(gold), "found_gold_count": len(gold & found),
                            "recall_at_5": round(len(gold & found) / len(gold), 4) if gold else "",
                            "latency_ms": response["latency_ms"], "api_calls": response["api_calls"], "error": response["error"] or "",
                            "answer_checked": "not_scored"})
    (out / "latest.json").write_text(json.dumps(run, ensure_ascii=False, indent=2))
    with (ROOT / "evaluation/results.csv").open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(results[0])); writer.writeheader(); writer.writerows(results)
    summary = []
    for (method, category), group in sorted(_group(results).items()):
        measured = [float(r["recall_at_5"]) for r in group if r["recall_at_5"] != ""]
        summary.append({"method": method, "category": category, "questions": len(group), "recall_denominator": len(measured),
                        "mean_recall_at_5": round(sum(measured) / len(measured), 4) if measured else "",
                        "mean_latency_ms": round(sum(float(r["latency_ms"]) for r in group) / len(group), 2),
                        "generated_answers": sum(bool(x["api_calls"]) and not x["error"] for x in group)})
    with (ROOT / "evaluation/summary.csv").open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(summary[0])); writer.writeheader(); writer.writerows(summary)
    print(json.dumps({"questions": len(questions), "rows": len(results), "mode": run["mode"], "run": str(out / "latest.json")}, ensure_ascii=False))


def _group(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[(row["method"], row["category"])].append(row)
    return groups


def main():
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("prepare")
    query = commands.add_parser("query")
    query.add_argument("question")
    query.add_argument("--method", choices=["rag", "graph_rag"], default="rag")
    query.add_argument("--retrieve-only", "--dry-run", action="store_true")
    evaluation = commands.add_parser("evaluate")
    evaluation.add_argument("--retrieve-only", action="store_true")
    evaluation.add_argument("--ids", nargs="+", help="Cùng tập ID cho cả hai phương pháp; hữu ích khi quota thấp")
    args = parser.parse_args()
    if args.command == "prepare": prepare()
    elif args.command == "query": print(json.dumps(answer(args.question, args.method, Searcher(), args.retrieve_only), ensure_ascii=False, indent=2))
    else:
        if not args.retrieve_only:
            raise SystemExit("Chạy với --retrieve-only; để đánh giá Gemini có checkpoint, dùng python -m evaluation.run_gemini")
        evaluate(True, args.ids)


if __name__ == "__main__":
    main()
