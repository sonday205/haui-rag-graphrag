"""CLI tái tạo corpus, hai cách truy xuất và phép đo truy xuất."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import time
import importlib.metadata
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
from src.index_store import index_directory, publish_index, read_index, sha256
from src.pacing import reserve_slot

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
REFUSAL = "Chưa xác định được từ tập tài liệu."
GENERATION_SCHEMA = {
    "type": "object", "properties": {
        "status": {"type": "string", "enum": ["answered", "insufficient_evidence"]},
        "answer": {"type": "string"},
        "cited_ids": {"type": "array", "items": {"type": "string"}},
    }, "required": ["status", "answer", "cited_ids"], "additionalProperties": False,
}


def validate_generation(raw: str | None, allowed_ids: list[str]) -> dict:
    """Xác nhận cấu trúc/citation; không thay thế chấm nội dung bằng chứng."""
    try:
        payload = json.loads(raw or "")
        text = payload["answer"].strip()
        status = payload["status"]
        cited = payload["cited_ids"]
        if not isinstance(cited, list) or any(not isinstance(item, str) for item in cited):
            raise ValueError("cited_ids không hợp lệ")
        if status == "insufficient_evidence":
            if text.rstrip(".").casefold() != REFUSAL.rstrip(".").casefold() or cited:
                raise ValueError("Nhánh từ chối chỉ được có câu từ chối chuẩn và không có citation")
            return {"status": status, "answer": REFUSAL, "cited_ids": []}
        # Một citation có thể chứa nhiều ID: [ID1, ID2]. Kiểm tra từng ID,
        # không bỏ qua ID lạ chỉ vì nó nằm trong cùng ngoặc với ID hợp lệ.
        mentioned = set()
        for group in re.findall(r"\[([^\[\]]+)\]", text):
            for item in group.split(","):
                item = item.strip()
                if not re.fullmatch(r"[A-Za-z0-9_-]+", item):
                    raise ValueError("Định dạng ID trong ngoặc không hợp lệ")
                mentioned.add(item)
        if status != "answered" or not text or not cited or set(cited) != mentioned or not set(cited) <= set(allowed_ids):
            raise ValueError("Đáp án phải dẫn ID chứng cứ hợp lệ, khớp danh sách cited_ids")
        return {"status": status, "answer": text, "cited_ids": list(dict.fromkeys(cited))}
    except (ValueError, KeyError, TypeError, AttributeError) as exc:
        raise ValueError(f"Mô hình không trả đáp án/trích dẫn hợp lệ: {exc}") from exc


def pipeline_sha256() -> str:
    digest = hashlib.sha256()
    for path in (ROOT / "src/project.py", ROOT / "src/ocr_corpus.py", ROOT / "src/legal_graph.py", ROOT / "src/index_store.py", ROOT / "src/pacing.py"):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def embedding_config() -> dict:
    return {"model": os.getenv("EMBEDDING_MODEL", CONFIG["embedding_model"]),
            "revision": CONFIG["embedding_revision"], "pooling": "normalized_window_mean_v1",
            "window_tokens": CONFIG["embedding_window_tokens"], "stride_tokens": CONFIG["embedding_stride_tokens"]}


def effective_config() -> dict:
    return {**CONFIG, "gemini_model": os.getenv("GEMINI_MODEL", CONFIG["gemini_model"]), "embedding": embedding_config()}


def runtime_versions() -> dict:
    names = ("torch", "transformers", "numpy", "scikit-learn", "networkx", "google-genai", "PyMuPDF")
    return {name: importlib.metadata.version(name) for name in names}


def index_fingerprint(directory: Path | None = None) -> dict:
    directory = directory or index_directory(ROOT)
    return {"corpus_sha256": sha256(directory / "articles.jsonl"),
            "vectors_sha256": sha256(directory / "vectors.npy"), "graph_sha256": sha256(directory / "graph.json")}


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
                     "document_number": "744/QĐ-ĐHCN; 666/QĐ-ĐHCN", "issued_date": "2021-08-19; 2023-06-01", "text": preface,
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
                             "document_number": "744/QĐ-ĐHCN; 666/QĐ-ĐHCN", "issued_date": "2021-08-19; 2023-06-01", "text": chunk.strip(),
                             "page_start": page_at(segment_start), "page_end": page_at(min(end - 1, segment_start + len(chunk))),
                             "source_url": "https://sict.haui.edu.vn/media/29/uffile-upload-no-title29811.pdf",
                             "landing_url": "https://sict.haui.edu.vn/vn/html/quy-che",
                             "source_sha256": sha, "source_char_start": segment_start,
                             "validity": "unknown"})
    if len({x["id"] for x in rows}) != len(rows):
        raise ValueError("ID điều khoản bị trùng")
    return rows


def model_encoder():
    name = os.getenv("EMBEDDING_MODEL", CONFIG["embedding_model"])
    revision = CONFIG["embedding_revision"]
    tokenizer = AutoTokenizer.from_pretrained(name, revision=revision)
    model = AutoModel.from_pretrained(name, revision=revision).eval()
    return tokenizer, model


def encode(texts: list[str], encoder=None) -> np.ndarray:
    tokenizer, model = encoder or model_encoder()
    settings = embedding_config()
    window = settings["window_tokens"]
    stride = settings["stride_tokens"]
    if not 0 <= stride < window - tokenizer.num_special_tokens_to_add():
        raise ValueError("Stride phải nhỏ hơn kích thước cửa sổ token")
    vectors = []
    with torch.inference_mode():
        for i in range(0, len(texts), 16):
            # Overflow giữ cả phần cuối của đoạn; ID/chứng cứ không phải chia lại.
            batch = tokenizer(texts[i:i + 16], padding=True, truncation=True, max_length=window,
                              stride=stride, return_overflowing_tokens=True, return_tensors="pt")
            owners = batch.pop("overflow_to_sample_mapping")
            windows = []
            for offset in range(0, len(owners), 16):
                inputs = {key: value[offset:offset + 16] for key, value in batch.items()}
                output = model(**inputs).last_hidden_state
                mask = inputs["attention_mask"].unsqueeze(-1)
                pooled = (output * mask).sum(1) / mask.sum(1).clamp(min=1)
                windows.append(torch.nn.functional.normalize(pooled, p=2, dim=1))
            pooled_windows = torch.cat(windows)
            # Trung bình các cửa sổ rồi chuẩn hóa, cùng một quy tắc cho hai pipeline.
            aggregated = torch.stack([pooled_windows[owners == sample].mean(0)
                                      for sample in range(len(texts[i:i + 16]))])
            vectors.append(torch.nn.functional.normalize(aggregated, p=2, dim=1).numpy())
    return np.vstack(vectors)


def build_graph(rows: list[dict]) -> nx.Graph:
    relations = reviewed_relations(ROOT, rows)
    return build_legal_graph(rows, relations, TOPICS, AUDIENCES)


def prepare() -> None:
    started = time.perf_counter()
    rows = build_articles() + build_ocr_articles(ROOT)
    if len({row["id"] for row in rows}) != len(rows):
        raise ValueError("ID đoạn corpus bị trùng")
    parsed = time.perf_counter()
    encoder = model_encoder()
    lengths = [len(encoder[0](row["text"], truncation=False)["input_ids"]) for row in rows]
    vectors = encode([r["text"] for r in rows], encoder)
    embedded = time.perf_counter()
    relations = reviewed_relations(ROOT, rows)
    graph = build_legal_graph(rows, relations, TOPICS, AUDIENCES)
    finished = time.perf_counter()
    metadata = {"timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "parse_ms": round((parsed - started) * 1000, 2),
                "vector_index_ms": round((embedded - parsed) * 1000, 2),
                "graph_index_ms": round((finished - embedded) * 1000, 2),
                "total_ms": round((finished - started) * 1000, 2),
                "embedding_config": embedding_config(), "runtime_versions": runtime_versions(),
                "code_sha256": pipeline_sha256(),
                "embedding_coverage": {"chunks": len(rows), "multi_window_chunks": sum(n > CONFIG["embedding_window_tokens"] for n in lengths),
                                       "max_input_tokens": max(lengths), "silent_truncation": False}}
    directory = publish_index(ROOT, rows, vectors, graph, relations, metadata)
    print(json.dumps({"documents": len(set(r["document_id"] for r in rows)),
                      "articles": len(set(r["article_id"] for r in rows if r["article_id"])),
                      "chunks": len(rows), "vector_dimensions": vectors.shape[1],
                      "graph_nodes": graph.number_of_nodes(), "graph_edges": graph.number_of_edges(),
                      "index_version": directory.name, "build_timing_ms": metadata}, ensure_ascii=False))


class Searcher:
    def __init__(self, encoder=None):
        self.directory, self.rows, self.vectors, self.graph, self.metadata = read_index(ROOT, embedding_config())
        self.by_id = {r["id"]: r for r in self.rows}
        self.encoder = encoder or model_encoder()
        self.lexical = TfidfVectorizer(analyzer="char", ngram_range=(2, 4), min_df=1)
        self.lexical_matrix = self.lexical.fit_transform([r["text"] for r in self.rows])

    def retrieve(self, question: str, method: str, k: int | None = None):
        k = k or CONFIG["top_k"]
        if method in ("rag", "hybrid"):
            query = encode([question], self.encoder)[0]
            scores = self.vectors @ query
            if method == "hybrid":
                lexical = (self.lexical_matrix @ self.lexical.transform([question]).T).toarray().ravel()
                scores = 0.55 * lexical + 0.45 * scores
            ranks = np.argsort(-scores)[:k]
            trace = {"method": "hybrid_no_graph" if method == "hybrid" else "vector_cosine", "top_k": k, "candidates": [{"id": self.rows[i]["id"], "score": round(float(scores[i]), 4)} for i in ranks]}
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
            raise ValueError("method phải là rag, hybrid hoặc graph_rag")
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


def answer(question: str, method: str, searcher: Searcher, retrieve_only: bool = False,
           min_interval_seconds: float | None = None) -> dict:
    start = time.perf_counter()
    evidence, trace = searcher.retrieve(question, method)
    retrieval_ms = (time.perf_counter() - start) * 1000
    ids = [r["id"] for r in evidence]
    citations = [{"article_id": r["id"], "label": r["title"] +
                  (f", Điều {r['article_number']}, khoản {r['clause']}" if r.get("article_number") and r.get("clause") not in (None, "title")
                   else f", Điều {r['article_number']}" if r.get("article_number") else "") +
                  f", trang {r['page_start']}" + (" (OCR chưa hiệu đính toàn bộ)" if r.get("extraction_method") == "user_supplied_ocr" else ""),
                  "url": r["source_url"] + f"#page={r['page_start']}"} for r in evidence]
    result = {"question": question, "method": method, "answer": None, "citations": citations if retrieve_only else [],
              "retrieved_article_ids": ids, "evidence": evidence, "retrieval_trace": trace,
              "latency_ms": None, "api_calls": 0, "token_usage": None, "error": None,
              "answer_status": "retrieve_only" if retrieve_only else None, "raw_answer": None,
              "retrieval_ms": round(retrieval_ms, 2), "pacing_wait_ms": 0.0, "request_started_utc": None,
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
                prompt = ("Trả lời tiếng Việt dựa DUY NHẤT vào các trích đoạn. Phân biệt số hiệu, phạm vi và phiên bản văn bản; "
                          "không suy đoán hiệu lực hiện hành. Một số đoạn là OCR chưa hiệu đính toàn bộ: "
                          "không khẳng định số liệu/chữ bị nhận dạng mơ hồ. Nếu thiếu chứng cứ, trả lời "
                          "JSON status=insufficient_evidence, answer='Chưa xác định được từ tập tài liệu.', cited_ids=[]. "
                          "Nhánh từ chối không được kèm khẳng định khác. Nếu trả lời được, status=answered, "
                          "viết câu trả lời có ID [đoạn] sát ý được hỗ trợ và liệt kê đúng các ID đó trong cited_ids. "
                          "Không viện dẫn ID ngoài danh sách.\nCâu hỏi: " + question + "\nChứng cứ:\n" +
                          "\n".join(f"[{r['id']}] Văn bản {r['document_id']} ({r.get('document_number') or 'chưa xác định số hiệu'}, "
                                    f"trang {r['page_start']}, hiệu lực hiện hành chưa xác minh; "
                                    f"{'OCR cần đối chiếu' if r.get('extraction_method') == 'user_supplied_ocr' else 'chữ PDF'}): {r['text']}"
                                    for r in evidence))
                with genai.Client(api_key=key, http_options=types.HttpOptions(
                        timeout=CONFIG["generation_timeout_ms"], retry_options=types.HttpRetryOptions(attempts=1))) as client:
                    result.update(reserve_slot(ROOT / "evaluation/runs/gemini_pacing.json",
                                               min_interval_seconds or CONFIG["min_api_interval_seconds"]))
                    result["api_calls"] = 1
                    response = client.models.generate_content(model=result["model"], contents=prompt,
                        config={"temperature": CONFIG["generation_temperature"],
                                "max_output_tokens": CONFIG["generation_max_output_tokens"],
                                "response_mime_type": "application/json", "response_json_schema": GENERATION_SCHEMA})
                result["raw_answer"] = response.text
                usage = getattr(response, "usage_metadata", None)
                result["token_usage"] = ({"input": getattr(usage, "prompt_token_count", None),
                    "output": getattr(usage, "candidates_token_count", None),
                    "thoughts": getattr(usage, "thoughts_token_count", None),
                    "total": getattr(usage, "total_token_count", None)} if usage else None)
                # Cả ID đoạn PDF và ID đoạn OCR đều phải xuất hiện trong chứng cứ.
                validated = validate_generation(response.text, ids)
                result["answer"] = validated["answer"]
                result["answer_status"] = validated["status"]
                result["citations"] = [c for c in citations if c["article_id"] in validated["cited_ids"]]
            except Exception as exc:
                detail = str(exc).replace(key, "[REDACTED]")
                if "503" in detail or "UNAVAILABLE" in detail:
                    result["error"] = "Gemini đang tạm quá tải (503). Vui lòng thử lại sau."
                elif "429" in detail or "RESOURCE_EXHAUSTED" in detail:
                    result["error"] = "Gemini đã chạm hạn mức (429). Vui lòng thử lại khi hạn mức được khôi phục."
                else:
                    result["error"] = f"Lỗi Gemini: {type(exc).__name__}: {detail[:1000]}"
        else:
            result["answer"] = REFUSAL
            result["answer_status"] = "insufficient_evidence"
    result["wall_ms"] = round((time.perf_counter() - start) * 1000, 2)
    result["latency_ms"] = round(result["wall_ms"] - result["pacing_wait_ms"], 2)
    assert all(c["article_id"] in ids for c in result["citations"])
    return result


def evaluate(retrieve_only: bool = False, selected_ids: list[str] | None = None, run_id: str | None = None) -> None:
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
    run_id = run_id or datetime.now(timezone.utc).strftime("retrieval_%Y%m%dT%H%M%S%f")
    if not re.fullmatch(r"[A-Za-z0-9_]+", run_id):
        raise ValueError("run_id chỉ nhận chữ, số và dấu gạch dưới")
    out = ROOT / "evaluation/runs" / run_id
    if out.exists():
        raise ValueError("Run đã tồn tại; chọn run_id mới")
    out.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).isoformat()
    run = {"timestamp_utc": timestamp, "mode": "retrieve_only" if retrieve_only else "generate",
              "config": effective_config(), "code_sha256": pipeline_sha256(),
              **index_fingerprint(searcher.directory), "runtime_versions": runtime_versions(),
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
    with (out / "results.csv").open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(results[0])); writer.writeheader(); writer.writerows(results)
    summary = []
    for (method, category), group in sorted(_group(results).items()):
        measured = [float(r["recall_at_5"]) for r in group if r["recall_at_5"] != ""]
        summary.append({"method": method, "category": category, "questions": len(group), "recall_denominator": len(measured),
                        "mean_recall_at_5": round(sum(measured) / len(measured), 4) if measured else "",
                        "mean_latency_ms": round(sum(float(r["latency_ms"]) for r in group) / len(group), 2),
                        "generated_answers": sum(bool(x["api_calls"]) and not x["error"] for x in group)})
    with (out / "summary.csv").open("w", newline="") as file:
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
    evaluation.add_argument("--run-id", help="Tên run mới; không ghi đè kết quả cũ")
    args = parser.parse_args()
    if args.command == "prepare": prepare()
    elif args.command == "query": print(json.dumps(answer(args.question, args.method, Searcher(), args.retrieve_only), ensure_ascii=False, indent=2))
    else:
        if not args.retrieve_only:
            raise SystemExit("Chạy với --retrieve-only; để đánh giá Gemini có checkpoint, dùng python -m evaluation.run_gemini")
        evaluate(True, args.ids, args.run_id)


if __name__ == "__main__":
    main()
