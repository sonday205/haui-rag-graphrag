"""Hồi quy cho các lỗi thực tế từ review, không gọi API thật."""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import numpy as np
from fastapi.testclient import TestClient

import server
from evaluation import run_gemini
from src import project as p
from src.index_store import publish_index, read_index, sha256
from src.legal_graph import mentioned_documents


class ResearchFixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = p.Searcher()
        cls.evidence, _ = cls.engine.retrieve("Sinh viên rút học phần khi nào?", "rag")

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        shutil.copytree(p.ROOT/"src", self.root/"src", ignore=shutil.ignore_patterns("__pycache__"))
        (self.root/"evaluation").mkdir()
        shutil.copy2(p.ROOT/"evaluation/questions.jsonl", self.root/"evaluation/questions.jsonl")
        self.meta = {k: v for k, v in self.engine.metadata.items() if k != "artifact_sha256"}
        self.relations = json.loads((self.engine.directory/"legal_relations.json").read_text())
        publish_index(self.root, self.engine.rows, self.engine.vectors, self.engine.graph, self.relations, self.meta)

    def tearDown(self):
        self.tmp.cleanup()

    def payload(self, text, status="answered", cited=None):
        return json.dumps({"status": status, "answer": text, "cited_ids": cited or []}, ensure_ascii=False)

    def test_mixed_refusal_is_blocked(self):
        with self.assertRaises(ValueError):
            p.validate_generation(self.payload(p.REFUSAL+" Tuy nhiên được nghỉ 100 ngày.", "insufficient_evidence"), [])

    def test_plain_refusal_and_supported_answer(self):
        self.assertEqual(p.validate_generation(self.payload(p.REFUSAL, "insufficient_evidence"), ["ID"])["cited_ids"], [])
        self.assertEqual(p.validate_generation(self.payload("Nội dung [ID]", cited=["ID"]), ["ID"])["status"], "answered")

    def test_unknown_missing_and_mismatched_ids(self):
        for text, cited in [("Nội dung [FAKE]", ["FAKE"]), ("Nội dung", ["ID"]), ("Nội dung [ID]", [])]:
            with self.subTest(text=text), self.assertRaises(ValueError):
                p.validate_generation(self.payload(text, cited=cited), ["ID"])

    def test_grouped_citations_validate_every_id(self):
        result = p.validate_generation(self.payload("Nội dung [ID1, ID2]", cited=["ID1", "ID2"]), ["ID1", "ID2"])
        self.assertEqual(result["cited_ids"], ["ID1", "ID2"])
        with self.assertRaises(ValueError):
            p.validate_generation(self.payload("Nội dung [ID1, FAKE]", cited=["ID1", "FAKE"]), ["ID1"])

    def test_empty_json_and_invalid_schema(self):
        for raw in (None, "", "không phải json", "[]", self.payload("")):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                p.validate_generation(raw, ["ID"])

    def test_failed_ocr_preserves_all_artifacts(self):
        before = {name: sha256(self.root/"data/processed"/name) for name in ("articles.jsonl", "vectors.npy", "graph.json")}
        with patch.object(p, "ROOT", self.root), patch.object(p, "build_articles", return_value=self.engine.rows), patch.object(p, "build_ocr_articles", side_effect=ValueError("bad OCR")):
            with self.assertRaises(ValueError): p.prepare()
        self.assertEqual(before, {name: sha256(self.root/"data/processed"/name) for name in before})

    def test_failed_embedding_preserves_all_artifacts(self):
        before = (self.root/"data/processed/current").resolve()
        with patch.object(p, "ROOT", self.root), patch.object(p, "build_articles", return_value=self.engine.rows), patch.object(p, "build_ocr_articles", return_value=[]), patch.object(p, "model_encoder", return_value=self.engine.encoder), patch.object(p, "encode", side_effect=RuntimeError("bad model")):
            with self.assertRaises(RuntimeError): p.prepare()
        self.assertEqual((self.root/"data/processed/current").resolve(), before)
        read_index(self.root, p.embedding_config())

    def test_invalid_publication_keeps_current(self):
        before = (self.root/"data/processed/current").resolve()
        with self.assertRaises(RuntimeError):
            publish_index(self.root, self.engine.rows, self.engine.vectors[:-1], self.engine.graph, self.relations, self.meta)
        self.assertEqual((self.root/"data/processed/current").resolve(), before)

    def test_health_missing_vector_returns_unready_and_503(self):
        (self.root/"data/processed/current/vectors.npy").unlink()
        with patch.object(server, "ROOT", self.root):
            client = TestClient(server.app)
            self.assertFalse(client.get("/api/health").json()["ready"])
            self.assertEqual(client.post("/api/chat", json={"question": "Hỏi quy chế", "retrieve_only": True}).status_code, 503)

    def test_hash_tampering_and_embedding_config_are_rejected(self):
        with self.assertRaises(RuntimeError): read_index(self.root, {"model": "wrong-model"})
        path = self.root/"data/processed/current/articles.jsonl"
        path.write_text(path.read_text()+"\n")
        with self.assertRaises(RuntimeError): read_index(self.root)

    def test_document_aliases_are_metadata_based(self):
        for number, year, doc in [("242", "2022", "NN_SICT"), ("427", "2022", "HP_SICT"), ("721", "2024", "QD721_2024")]:
            a = mentioned_documents(f"Quyết định {number}/{year}", self.engine.graph)
            b = mentioned_documents(f"Quyết định {number} năm {year}", self.engine.graph)
            self.assertEqual(a, b)
            self.assertIn("Document:"+doc, b)

    def test_long_embedding_keeps_tail(self):
        prefix = "quy chế đào tạo sinh viên " * 100
        a = p.encode([prefix + "được tốt nghiệp và cấp bằng" * 50], self.engine.encoder)
        b = p.encode([prefix + "bị kỷ luật buộc thôi học" * 50], self.engine.encoder)
        self.assertGreater(np.linalg.norm(a-b), 0.01)
        self.assertTrue(np.allclose(np.linalg.norm(a, axis=1), 1, atol=1e-5))

    def test_checkpoint_model_switch_rejected(self):
        with patch.object(run_gemini, "ROOT", self.root), patch.object(run_gemini, "Searcher", return_value=self.engine), patch.object(sys, "argv", ["run_gemini", "--run-id", "modeltest", "--ids", "S02", "--max-new-calls", "0"]), patch.dict(os.environ, {"GEMINI_API_KEY": "fake-key"}):
            with patch.dict(os.environ, {"GEMINI_MODEL": "model-A"}): run_gemini.main()
            with patch.dict(os.environ, {"GEMINI_MODEL": "model-B"}), self.assertRaises(SystemExit): run_gemini.main()

    def test_compare_skips_second_call_on_provider_error(self):
        for code in (503, 429, 403, 404):
            client_mock = MagicMock()
            client_mock.__enter__.return_value.models.generate_content.side_effect = RuntimeError(str(code))
            with patch.object(server, "searcher", return_value=self.engine), patch("google.genai.Client", return_value=client_mock), patch.object(p, "reserve_slot", return_value={"pacing_wait_ms": 0, "request_started_utc": None}), patch.dict(os.environ, {"GEMINI_API_KEY": "fake-key"}):
                result = TestClient(server.app).post("/api/chat", json={"question": "Sinh viên rút học phần khi nào?"}).json()["results"]
                self.assertEqual(result["rag"]["api_calls"], 1)
                self.assertEqual(result["graph_rag"]["api_calls"], 0)

    def test_api_modes_validation_and_missing_key(self):
        with patch.object(server, "searcher", return_value=self.engine):
            client = TestClient(server.app)
            self.assertTrue(client.get("/api/health").json()["ready"])
            self.assertEqual(client.get("/api/suggestions").status_code, 200)
            for mode in ("rag", "graph_rag", "compare"):
                r = client.post("/api/chat", json={"question": "Sinh viên rút học phần khi nào?", "mode": mode, "retrieve_only": True})
                self.assertEqual(r.status_code, 200)
                self.assertTrue(all(x["api_calls"] == 0 for x in r.json()["results"].values()))
            for q in ("x", "   ", "a"*2001):
                self.assertEqual(client.post("/api/chat", json={"question": q}).status_code, 422)
            with patch.dict(os.environ, {"GEMINI_API_KEY": ""}):
                results = client.post("/api/chat", json={"question": "Sinh viên rút học phần khi nào?"}).json()["results"]
                self.assertTrue(all(r["error"] and not r["api_calls"] for r in results.values()))


if __name__ == "__main__":
    unittest.main()
