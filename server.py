"""API cho giao diện hỏi đáp quy chế; API key chỉ tồn tại ở máy chủ."""
from __future__ import annotations

import os
from functools import lru_cache
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from src.project import CONFIG, ROOT, Searcher, answer, read_jsonl, embedding_config, effective_config
from src.index_store import index_directory, read_index

app = FastAPI(title="HaUI Quy chế AI", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


class ChatRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    mode: Literal["compare", "rag", "graph_rag"] = "compare"
    retrieve_only: bool = False


@lru_cache(maxsize=1)
def cached_searcher(version: str, encoder_config: str) -> Searcher:
    return Searcher()


def searcher() -> Searcher:
    return cached_searcher(str(index_directory(ROOT)), str(embedding_config()))


@app.get("/api/health")
def health():
    try:
        directory, corpus, _, _, _ = read_index(ROOT, embedding_config())
        ready, error = True, None
    except RuntimeError as exc:
        corpus, directory, ready, error = [], None, False, str(exc)
    return {"ready": ready, "index_error": error, "index_version": directory.name if directory else None,
            "key_configured": bool(os.getenv("GEMINI_API_KEY")),
            "model": effective_config()["gemini_model"],
            "corpus_documents": len({row["document_id"] for row in corpus}),
            "corpus_chunks": len(corpus),
            "ocr_documents": len({row["document_id"] for row in corpus if row.get("extraction_method") == "user_supplied_ocr"}),
            "validity": "unknown"}


@app.get("/api/suggestions")
def suggestions():
    by_id = {q["question_id"]: q for q in read_jsonl(ROOT / "evaluation/questions.jsonl")}
    chosen = ("S02", "M01", "U01", "V02", "S08", "M03")
    return [{"id": by_id[qid]["question_id"], "question": by_id[qid]["question"],
             "category": by_id[qid]["category"]} for qid in chosen if qid in by_id]


@app.post("/api/chat")
def chat(request: ChatRequest):
    question = request.question.strip()
    if len(question) < 3:
        raise HTTPException(status_code=422, detail="Câu hỏi phải có ít nhất 3 ký tự")
    try:
        read_index(ROOT, embedding_config())
        engine = searcher()
        methods = ("rag", "graph_rag") if request.mode == "compare" else (request.mode,)
        responses = {}
        provider_blocked = False
        for method in methods:
            skip_generation = request.retrieve_only or provider_blocked
            result = answer(question, method, engine, skip_generation)
            if provider_blocked:
                result["error"] = "Gemini vừa trả lỗi dịch vụ; chỉ hiển thị chứng cứ truy xuất cho phương pháp này."
            if not skip_generation and result["error"] and any(
                code in result["error"] for code in ("429", "503", "403", "404")
            ):
                provider_blocked = True
            responses[method] = result
        return {"question": question, "mode": request.mode,
                "retrieve_only": request.retrieve_only, "results": responses}
    except (RuntimeError, OSError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


dist = ROOT / "frontend/dist"
if dist.exists():
    app.mount("/", StaticFiles(directory=dist, html=True), name="frontend")
