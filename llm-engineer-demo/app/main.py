"""FastAPI app entry — Vietnamese Legal Assistant (Module I).

Chạy dev server:
    uvicorn app.main:app --reload

Mở docs tương tác: http://localhost:8000/docs
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api import routes_admin, routes_chat, routes_multi_agent, routes_pr
from app.config import settings
from app.guardrails.checks import GuardrailViolation

app = FastAPI(
    title=settings.app_name,
    description="RAG chatbot pháp lý (Module I) + Personal Assistant agent (Module II).",
    version="0.1.0",
)

# Cho phép frontend tĩnh (Website_show_yourself, mở qua file:// hoặc một static
# server khác cổng/khác origin) gọi thẳng API này khi demo trên cùng máy.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes_chat.router)
app.include_router(routes_admin.router)
app.include_router(routes_multi_agent.router)
app.include_router(routes_pr.router)

_STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")
app.mount("/portfolio", StaticFiles(directory=_STATIC_DIR / "portfolio", html=True), name="portfolio")


@app.get("/", tags=["meta"])
def agent_pr_ui() -> FileResponse:
    """Demo UI mặc định — Hierarchical VN-stock agent (xem app/static/agent_pr.html).

    Module II (Personal Assistant, routes_assistant) tắt hẳn khỏi router phía
    trên — không mount qua main.py. app/agent (CRAG, /chat/agent) vẫn còn
    trong routes_chat.router nhưng không link từ UI mặc định nữa; gọi trực
    tiếp qua /docs nếu cần. Module I chat.html cũ vẫn phục vụ tại /legal-chat.
    """
    return FileResponse(_STATIC_DIR / "agent_pr.html")


@app.get("/legal-chat", tags=["meta"])
def legal_chat_ui() -> FileResponse:
    """UI cũ Module I (RAG + CRAG) — xem app/static/chat.html. Tab Assistant (M2)
    trong trang này sẽ lỗi vì /assistant/* đã tắt khỏi router (xem agent_pr_ui)."""
    return FileResponse(_STATIC_DIR / "chat.html")


@app.get("/swarm-handoff-map.html", tags=["meta"])
def swarm_handoff_map() -> FileResponse:
    """Sơ đồ kiến trúc Crawler Swarm đề xuất (link từ portfolio) — xem app/static/swarm-handoff-map.html."""
    return FileResponse(_STATIC_DIR / "swarm-handoff-map.html")


@app.exception_handler(GuardrailViolation)
def guardrail_violation_handler(request: Request, exc: GuardrailViolation) -> JSONResponse:
    """Input bị guardrails chặn (Buổi 7) → HTTP 400 với lý do rõ ràng."""
    return JSONResponse(
        status_code=400,
        content={"error": "input_rejected", "reason": exc.reason, "details": exc.details},
    )


@app.get("/health", tags=["meta"])
def health() -> dict:
    """Health check — không gọi LLM, không cần API key."""
    return {
        "status": "ok",
        "app": settings.app_name,
        "model": settings.llm_model,
        "keys_configured": len(settings.api_keys),
    }
