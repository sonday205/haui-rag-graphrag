"""API cho giao diện hỏi đáp quy chế; API key chỉ tồn tại ở máy chủ."""
from __future__ import annotations

import os
import threading
import time
from functools import lru_cache
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from src.project import ARTICLES, CONFIG, ROOT, Searcher, answer, read_jsonl

app = FastAPI(title="HaUI Quy chế AI", version="1.0.0")
_gemini_pacing_lock = threading.Lock()
_last_gemini_start = 0.0
_min_gemini_interval_seconds = 5.0
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
def searcher() -> Searcher:
    if not ARTICLES.exists():
        raise RuntimeError("Thiếu chỉ mục; chạy python -m src.project prepare")
    return Searcher()


def wait_for_gemini_slot() -> None:
    """Giãn các lời gọi từ giao diện để không vượt 15 lượt/phút trong một tiến trình."""
    global _last_gemini_start
    with _gemini_pacing_lock:
        remaining = _min_gemini_interval_seconds - (time.monotonic() - _last_gemini_start)
        if remaining > 0:
            time.sleep(remaining)
        _last_gemini_start = time.monotonic()


@app.get("/api/health")
def health():
    corpus = read_jsonl(ARTICLES) if ARTICLES.exists() else []
    return {"ready": ARTICLES.exists(), "key_configured": bool(os.getenv("GEMINI_API_KEY")),
            "model": os.getenv("GEMINI_MODEL", CONFIG["gemini_model"]),
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
    if not ARTICLES.exists():
        raise HTTPException(status_code=503, detail="Chỉ mục chưa được tạo")
    question = request.question.strip()
    if len(question) < 3:
        raise HTTPException(status_code=422, detail="Câu hỏi phải có ít nhất 3 ký tự")
    try:
        engine = searcher()
        methods = ("rag", "graph_rag") if request.mode == "compare" else (request.mode,)
        responses = {}
        provider_blocked = False
        for method in methods:
            skip_generation = request.retrieve_only or provider_blocked
            if not skip_generation and os.getenv("GEMINI_API_KEY"):
                wait_for_gemini_slot()
            result = answer(question, method, engine, skip_generation)
            if provider_blocked:
                result["error"] = "Gemini vừa trả lỗi dịch vụ; chỉ hiển thị chứng cứ truy xuất cho phương pháp này."
            if not skip_generation and result["error"] and any(
                code in result["error"] for code in ("429", "503")
            ):
                provider_blocked = True
            responses[method] = result
        return {"question": question, "mode": request.mode,
                "retrieve_only": request.retrieve_only, "results": responses}
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


dist = ROOT / "frontend/dist"
if dist.exists():
    app.mount("/", StaticFiles(directory=dist, html=True), name="frontend")
