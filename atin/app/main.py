"""FastAPI app — agent_stat (Text-to-SQL, chatbot thống kê ra/vào khu vực, Phase 1).

Chạy dev server:
    uvicorn app.main:app --reload --app-dir atin

Mở docs tương tác: http://localhost:8000/docs
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.config import settings
from app.guardrails.checks import GuardrailViolation
from app.supervisor_agent import Agent_Input, run_supervisor

app = FastAPI(title=settings.app_name, description="Chatbot thống kê Text-to-SQL (Phase 1).", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

_STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")


class AskRequest(BaseModel):
    question: str = Field(min_length=1, description="Câu hỏi thống kê tự nhiên")
    thread_id: str = ""


class AskResponse(BaseModel):
    question: str
    answer: str
    sql: str = ""
    row_count: int = 0


@app.post("/stat/ask", response_model=AskResponse, tags=["agent-stat"])
async def ask(req: AskRequest) -> AskResponse:
    try:
        out = run_supervisor(Agent_Input(question=req.question, thread_id=req.thread_id))
    except GuardrailViolation:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Không trả lời được: {exc}") from exc
    query = out.stat.query if out.stat else None
    return AskResponse(
        question=out.question,
        answer=out.answer,
        sql=query.sql if query else "",
        row_count=query.row_count if query else 0,
    )


@app.get("/", tags=["meta"])
def ui() -> FileResponse:
    return FileResponse(_STATIC_DIR / "index.html")


@app.exception_handler(GuardrailViolation)
def guardrail_violation_handler(request: Request, exc: GuardrailViolation) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={"error": "input_rejected", "reason": exc.reason, "details": exc.details},
    )


@app.get("/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok", "app": settings.app_name, "model": settings.llm_model}
