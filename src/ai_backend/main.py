"""AI Backend Microservice — FastAPI Entrypoint (Cổng 8001).

Chỉ phục vụ:
- /health: Trạng thái hoạt động của AI Engine, Swarm StateGraph, tài nguyên phụ trợ.
- /v1/chat/stream (và alias /chat/stream): Luồng phản hồi Server-Sent Events (SSE).
- /v1/scan (và alias /scan): Quét phân tích kỹ thuật và cảnh báo mã cổ phiếu.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ai_backend.api.helpers.exception_handler import register_ai_exception_handlers
from ai_backend.api.helpers.middlewares import CorrelationIdMiddleware, RequestLoggingMiddleware
from ai_backend.api.routers import (
    chat_stream_alias_router,
    chat_stream_router,
    health_router,
    scan_alias_router,
    scan_router,
)
from ai_backend.shared.settings import ai_settings
from common.logging.logger import get_logger, setup_logging

setup_logging(ai_settings.log_level)
logger = get_logger("ai_backend.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Quản lý vòng đời khởi động và dừng của AI Backend."""
    logger.info(
        f"Khởi động AI Backend Microservice tại http://{ai_settings.host}:{ai_settings.port} "
        f"[LLM={ai_settings.llm_backend}, Qdrant={ai_settings.qdrant_host}:{ai_settings.qdrant_port}, "
        f"Fallback={ai_settings.price_fallback_on_error}]"
    )

    try:
        from ai_backend.infra.market_data import VnstockPriceSource, CafefNewsSource
        from ai_backend.infra.storage import (
            SqliteMemoryStore,
            SqlitePriceHistoryStore,
            SqliteWatchlistStore,
        )
        from ai_backend.infra.graph.chat import run_chat_graph
        from ai_backend.application.swarm_orchestrator import SwarmOrchestrator
        from ai_backend.api.deps import set_ai_deps, AiDeps

        db_path = ai_settings.sqlite_path
        price_source = VnstockPriceSource(fallback_on_error=ai_settings.price_fallback_on_error)
        news_source = CafefNewsSource()
        history_store = SqlitePriceHistoryStore(db_path)
        memory_store = SqliteMemoryStore(db_path)
        watchlist_store = SqliteWatchlistStore(db_path)

        orchestrator = SwarmOrchestrator(
            graph_runner=run_chat_graph,
            price_source=price_source,
            news_source=news_source,
            history_store=history_store,
            memory_store=memory_store,
            watchlist_store=watchlist_store,
        )

        deps = AiDeps(
            swarm_orchestrator=orchestrator,
            price_source=price_source,
            news_source=news_source,
        )
        set_ai_deps(deps)
        logger.info("[OK] SwarmOrchestrator đã được khởi tạo và kết nối thành công.")
    except Exception as exc:
        logger.warning(f"Không thể khởi tạo SwarmOrchestrator: {exc}", exc_info=True)

    yield
    logger.info("Dừng AI Backend Microservice.")


# Khởi tạo ứng dụng FastAPI AI Backend
app = FastAPI(
    title=ai_settings.app_name,
    version=ai_settings.version,
    description="AI Backend Microservice — LangGraph Swarm Multi-Agent, SSE Streaming & Technical Scanner.",
    lifespan=lifespan,
)

# 1. Đăng ký Middlewares
app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ai_settings.cors_origins if ai_settings.cors_origins else ["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Đăng ký Global Exception Handlers
register_ai_exception_handlers(app)

# 3. Đăng ký các Router nghiệp vụ AI Backend
app.include_router(health_router)
app.include_router(chat_stream_router)
app.include_router(chat_stream_alias_router)
app.include_router(scan_router)
app.include_router(scan_alias_router)


if __name__ == "__main__":
    import uvicorn

    logger.info(f"AI Service chạy trên http://{ai_settings.host}:{ai_settings.port}")
    uvicorn.run(
        "ai_backend.main:app",
        host=ai_settings.host,
        port=ai_settings.port,
        reload=False,
    )
