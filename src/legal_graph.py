"""Đồ thị chứng cứ: cạnh pháp lý có văn bản/trang, cạnh chủ đề chỉ để truy xuất."""
from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from pathlib import Path

import networkx as nx

from src.ocr_corpus import pages_from_markdown

LEGAL_RELATIONS = {"AMENDS", "REPLACES", "SUPPLEMENTS", "CONSOLIDATES", "CITES"}


def normalized(text: str) -> str:
    return re.sub(r"\s+", " ", text).casefold().strip()


def relation_intents(question: str) -> set[str]:
    text = normalized(question)
    intents = set()
    for phrase, relation in (("thay thế", "REPLACES"), ("sửa đổi", "AMENDS"),
                             ("bổ sung", "SUPPLEMENTS"), ("hợp nhất", "CONSOLIDATES"),
                             ("viện dẫn", "CITES"), ("căn cứ", "CITES"),
                             ("dựa trên", "CITES")):
        if phrase in text:
            intents.add(relation)
    if "quan hệ" in text or "xử lý văn bản" in text:
        intents.update(LEGAL_RELATIONS)
    return intents


def mentioned_documents(question: str, graph: nx.MultiDiGraph) -> set[str]:
    """Nhận diện số hiệu/năm rõ trong câu hỏi; không đoán tên văn bản chỉ từ chủ đề."""
    text = normalized(question)
    matched = set()
    for node, data in graph.nodes(data=True):
        if data.get("kind") != "Document":
            continue
        for number, year in data.get("number_year_aliases", []):
            # Chấp nhận số/năm và số ... năm, có ranh giới để tránh 242 khớp 1242.
            if re.search(rf"(?<!\d)0?{re.escape(number)}(?!\d)", text) and re.search(rf"(?<!\d){year}(?!\d)", text):
                matched.add(node)
        if data.get("is_consolidated") and "bản hợp nhất" in text:
            matched.add(node)
        title = normalized(data.get("title", ""))
        title_without_year = re.sub(r"\s+\d{4}$", "", title)
        if len(title_without_year) >= 24 and title_without_year in text:
            matched.add(node)
    return matched


def number_year_aliases(document_number: str, issued_date: str) -> list[list[str]]:
    numbers = re.findall(r"(\d+)\s*/", document_number)
    dates = re.findall(r"(?<!\d)(\d{4})(?!\d)", issued_date)
    if len(numbers) == len(dates):
        return [[str(int(number)), year] for number, year in zip(numbers, dates)]
    if len(dates) == 1:
        return [[str(int(number)), dates[0]] for number in numbers]
    return []


def reviewed_relations(root: Path, rows: list[dict]) -> list[dict]:
    """Từ chối cạnh thiếu câu dẫn trong đúng trang của đúng văn bản."""
    with (root / "data/source_manifest.csv").open(newline="", encoding="utf-8") as file:
        manifest = {record["id"]: record for record in csv.DictReader(file)}
    chunks_by_page = defaultdict(list)
    for row in rows:
        chunks_by_page[(row["document_id"], row["page_start"])].append(row)
    ocr_pages = {}
    for document_id, record in manifest.items():
        if not record["local_path"]:
            continue
        path = root / "data/ocr" / (Path(record["local_path"]).stem + ".md")
        if path.exists():
            ocr_pages[document_id] = dict(pages_from_markdown(path))
    definitions = json.loads((root / "data/relations_reviewed.json").read_text(encoding="utf-8"))
    validated = []
    for edge in definitions:
        if edge["relation"] not in LEGAL_RELATIONS:
            raise ValueError(f"Loại cạnh chưa duyệt: {edge['relation']}")
        doc = edge["evidence_document"]
        page = edge["evidence_page"]
        if doc not in ocr_pages or page not in ocr_pages[doc]:
            raise ValueError(f"Không có trang chứng cứ: {doc}, trang {page}")
        if normalized(edge["evidence_text"]) not in normalized(ocr_pages[doc][page]):
            raise ValueError(f"Câu dẫn không xuất hiện ở {doc}, trang {page}: {edge['evidence_text']}")
        candidates = chunks_by_page[(doc, page)]
        if not candidates:
            raise ValueError(f"Không có đoạn chỉ mục ở {doc}, trang {page}")
        needle = normalized(edge["evidence_text"])
        witness = next((row for row in candidates if needle in normalized(row["text"])), None)
        if witness is None:
            raise ValueError(f"Câu dẫn không nằm trong một đoạn chỉ mục: {doc}, trang {page}")
        record = manifest[doc]
        validated.append({**edge, "evidence_article_ids": [witness["id"]],
            "evidence_url": record["file_url"] + f"#page={page}",
            "review_status": "ocr_page_and_chunk_verified", "validity_claim": "none"})
    keys = [(r["source"], r["relation"], r["target"]) for r in validated]
    if len(keys) != len(set(keys)):
        raise ValueError("Cạnh pháp lý bị trùng")
    return validated


def build_legal_graph(rows: list[dict], relations: list[dict], topics: dict, audiences: dict) -> nx.MultiDiGraph:
    graph = nx.MultiDiGraph()
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["document_id"]].append(row)
    for document_id, chunks in grouped.items():
        graph.add_node("Document:" + document_id, kind="Document", label=document_id,
                       corpus_present=True, title=chunks[0]["title"],
                       document_number=chunks[0].get("document_number") or "",
                       issued_date=chunks[0].get("issued_date") or "",
                       number_year_aliases=number_year_aliases(chunks[0].get("document_number") or "", chunks[0].get("issued_date") or ""),
                       is_consolidated="hợp nhất" in chunks[0]["title"].casefold(),
                       validity="unknown", source_url=chunks[0]["source_url"])
        previous = None
        for row in chunks:
            chunk_node = "Article:" + row["id"]
            graph.add_node(chunk_node, kind="Article", label=row["id"],
                           document_id=document_id, page=row["page_start"])
            graph.add_edge("Document:" + document_id, chunk_node, relation="CONTAINS",
                           evidence_article_ids=[row["id"]])
            if previous:
                graph.add_edge(previous, chunk_node, relation="NEXT",
                               evidence_article_ids=[row["id"]])
            previous = chunk_node
            lower = row["text"].casefold()
            for topic, terms in topics.items():
                if any(term.casefold() in lower for term in terms):
                    node = "Topic:" + topic
                    graph.add_node(node, kind="Topic", label=topic)
                    graph.add_edge(chunk_node, node, relation="ABOUT",
                                   evidence_article_ids=[row["id"]])
            for audience, term in audiences.items():
                if term.casefold() in lower:
                    node = "Audience:" + audience
                    graph.add_node(node, kind="Audience", label=audience)
                    graph.add_edge(chunk_node, node, relation="APPLIES_TO",
                                   evidence_article_ids=[row["id"]])
    for edge in relations:
        for document_id in (edge["source"], edge["target"]):
            node = "Document:" + document_id
            if node not in graph:
                # Các nút tham chiếu không có toàn văn: alias lấy từ số hiệu chuẩn trong registry cạnh.
                reference = re.fullmatch(r"(?:QD|TT)(\d+)_(\d{4})", document_id)
                graph.add_node(node, kind="Document", label=document_id,
                               corpus_present=False, validity="unknown",
                               number_year_aliases=[list(reference.groups())] if reference else [])
        graph.add_edge("Document:" + edge["source"], "Document:" + edge["target"],
                       **{key: value for key, value in edge.items() if key not in ("source", "target")})
    return graph
