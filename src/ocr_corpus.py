"""Đưa bản OCR do người dùng cung cấp vào corpus, giữ liên kết tới từng trang PDF."""
from __future__ import annotations

import csv
import hashlib
import re
from pathlib import Path

PAGE_HEADING = re.compile(r"(?m)^## Trang (\d+)\s*$")
MAX_CHARS = 1000


def pages_from_markdown(path: Path) -> list[tuple[int, str]]:
    source = path.read_text(encoding="utf-8")
    headings = list(PAGE_HEADING.finditer(source))
    if not headings:
        raise ValueError(f"Không có mốc trang trong {path}")
    pages = []
    for index, heading in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(source)
        pages.append((int(heading.group(1)), source[heading.end():end].strip()))
    if [number for number, _ in pages] != list(range(1, len(pages) + 1)):
        raise ValueError(f"Số trang OCR không liên tục trong {path}")
    return pages


def split_text(text: str, limit: int = MAX_CHARS) -> list[str]:
    """Giữ nguyên chữ OCR; ghép dòng, chia ở ranh giới từ trong cùng một trang."""
    clean = re.sub(r"\s+", " ", text).strip()
    chunks = []
    while clean:
        if len(clean) <= limit:
            chunks.append(clean)
            break
        cut = clean.rfind(" ", 0, limit + 1)
        if cut < limit // 2:
            cut = limit
        chunks.append(clean[:cut].strip())
        clean = clean[cut:].strip()
    return [chunk for chunk in chunks if len(chunk) >= 20]


def build_ocr_articles(root: Path) -> list[dict]:
    with (root / "data/source_manifest.csv").open(newline="", encoding="utf-8") as file:
        manifest = list(csv.DictReader(file))
    rows = []
    for document in manifest:
        if document["id"] == "QC2023" or not document["local_path"]:
            continue
        source = root / document["local_path"]
        ocr = root / "data/ocr" / f"{source.stem}.md"
        if not ocr.exists():
            raise FileNotFoundError(f"Thiếu bản OCR của {source.name}: {ocr}")
        if hashlib.sha256(source.read_bytes()).hexdigest() != document["sha256"]:
            raise ValueError(f"PDF đã khác SHA trong manifest: {source}")
        pages = pages_from_markdown(ocr)
        if len(pages) != int(document["pages"]):
            raise ValueError(f"OCR {ocr.name} có {len(pages)} trang, PDF có {document['pages']}")
        ocr_sha = hashlib.sha256(ocr.read_bytes()).hexdigest()
        if document.get("ocr_sha256") and ocr_sha != document["ocr_sha256"]:
            raise ValueError(f"OCR đã khác SHA trong manifest: {ocr}")
        for page_number, text in pages:
            for index, chunk in enumerate(split_text(text), 1):
                row_id = f"{document['id']}-P{page_number:03d}-C{index:02d}"
                rows.append({
                    "id": row_id, "document_id": document["id"],
                    "article_id": None, "article_number": None, "clause": None,
                    "title": document["title"], "document_number": document["document_number"],
                    "issued_date": document["issued_date"], "text": chunk,
                    "page_start": page_number, "page_end": page_number,
                    "source_url": document["file_url"], "landing_url": document["page_url"],
                    "source_sha256": document["sha256"], "ocr_sha256": ocr_sha,
                    "extraction_method": "user_supplied_ocr", "ocr_review_status": "page_matched_unreviewed",
                    "validity": "unknown",
                })
    if len({row["id"] for row in rows}) != len(rows):
        raise ValueError("ID đoạn OCR bị trùng")
    return rows
