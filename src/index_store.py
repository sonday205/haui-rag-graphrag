"""Lưu cả bộ chỉ mục theo phiên bản; current đổi bằng một thao tác atomic."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import uuid
from pathlib import Path

import networkx as nx
import numpy as np

FILES = ("articles.jsonl", "vectors.npy", "graph.json", "legal_relations.json", "build_meta.json")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def index_directory(root: Path) -> Path:
    processed = root / "data/processed"
    current = processed / "current"
    if current.is_symlink() or current.exists():
        return current.resolve(strict=True)
    return processed


def read_index(root: Path, embedding_config: dict | None = None):
    """Pin một phiên bản trước khi đọc để không trộn artifact khi current đổi."""
    try:
        directory = index_directory(root)
        paths = {name: directory / name for name in FILES}
        for path in paths.values():
            if not path.is_file():
                raise ValueError(f"Thiếu {path.name}")
        meta = json.loads(paths["build_meta.json"].read_text())
        hashes = meta.get("artifact_sha256")
        if not hashes:
            raise ValueError("Chỉ mục cũ chưa có manifest kiểm tra; chạy prepare để nâng cấp")
        if any(sha256(paths[name]) != digest for name, digest in hashes.items()):
            raise ValueError("Hash artifact không khớp manifest chỉ mục")
        if embedding_config is not None and meta.get("embedding_config") != embedding_config:
            raise ValueError("Encoder/cách embedding đã đổi; cần dựng lại chỉ mục")
        rows = [json.loads(line) for line in paths["articles.jsonl"].read_text().splitlines() if line.strip()]
        vectors = np.load(paths["vectors.npy"], allow_pickle=False)
        graph = nx.node_link_graph(json.loads(paths["graph.json"].read_text()), edges="links")
        ids = {row["id"] for row in rows}
        if not rows or len(ids) != len(rows) or vectors.ndim != 2 or len(vectors) != len(rows):
            raise ValueError("ID corpus hoặc kích thước vector không khớp")
        if not np.isfinite(vectors).all() or not np.allclose(np.linalg.norm(vectors, axis=1), 1, atol=1e-5):
            raise ValueError("Vector không hữu hạn/chuẩn hóa")
        graph_ids = {node.removeprefix("Article:") for node, data in graph.nodes(data=True) if data.get("kind") == "Article"}
        if graph_ids != ids:
            raise ValueError("ID đoạn trong graph khác corpus")
        relations = json.loads(paths["legal_relations.json"].read_text())
        if any(not set(edge["evidence_article_ids"]) <= ids for edge in relations):
            raise ValueError("Cạnh pháp lý trỏ ra ngoài corpus")
        return directory, rows, vectors, graph, meta
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise RuntimeError(f"Chỉ mục không sẵn sàng: {exc}") from exc


def publish_index(root: Path, rows: list[dict], vectors: np.ndarray, graph, relations: list[dict], metadata: dict) -> Path:
    processed = root / "data/processed"
    versions = processed / "versions"
    versions.mkdir(parents=True, exist_ok=True)
    # Lưu bộ cũ nguyên vẹn trước lần nâng cấp đầu tiên.
    legacy = versions / "legacy_pre_atomic"
    if not (processed / "current").is_symlink() and not legacy.exists():
        legacy.mkdir()
        for name in FILES:
            if (processed / name).is_file():
                shutil.copy2(processed / name, legacy / name)
    with tempfile.TemporaryDirectory(prefix=".staging-", dir=versions) as temporary:
        stage = Path(temporary)
        (stage / "articles.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows))
        np.save(stage / "vectors.npy", vectors)
        (stage / "graph.json").write_text(json.dumps(nx.node_link_data(graph, edges="links"), ensure_ascii=False))
        (stage / "legal_relations.json").write_text(json.dumps(relations, ensure_ascii=False, indent=2))
        metadata = {**metadata, "artifact_sha256": {name: sha256(stage / name) for name in FILES if name != "build_meta.json"}}
        (stage / "build_meta.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2))
        # read_index đọc qua root/data/processed; kiểm tra staging bằng root tạm.
        with tempfile.TemporaryDirectory(prefix="haui-index-check-") as check_root:
            fake_root = Path(check_root)
            (fake_root / "data").mkdir()
            (fake_root / "data/processed").symlink_to(stage)
            read_index(fake_root, metadata["embedding_config"])
        destination = versions / uuid.uuid4().hex
        os.replace(stage, destination)
    pointer = processed / (".current-" + uuid.uuid4().hex)
    pointer.symlink_to(destination.relative_to(processed), target_is_directory=True)
    os.replace(pointer, processed / "current")
    # Giữ các đường dẫn cũ trong README/CLI; bộ đọc chính luôn pin current.
    for name in FILES:
        link = processed / (".link-" + uuid.uuid4().hex)
        link.symlink_to(Path("current") / name)
        os.replace(link, processed / name)
    return destination
