"""AI Backend Microservice — FastAPI Entrypoint (Cổng 8001).

Chỉ phục vụ:
- /health: Trạng thái hoạt động của AI Engine, Swarm StateGraph, tài nguyên phụ trợ.
- /v1/chat, /v1/chat/stream-sse: Hỏi-đáp → team chat của Hierarchical Swarm (JSON / Server-Sent Events).
- /v1/scan: Quét cảnh báo một mã → team scan của Hierarchical Swarm.
- /v1/concepts/ingest: Upload file markdown khái niệm (multipart) → Qdrant.

Job nền: quét toàn bộ watchlist mỗi `SCAN_INTERVAL_MINUTES` phút (biến môi trường), cũng qua team scan.
Cả hai nhánh chạy chung MỘT graph (domain/agents/graph.py).
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ai_backend.api.helpers.exception_handler import register_ai_exception_handlers
from ai_backend.api.helpers.middlewares import CorrelationIdMiddleware, RequestLoggingMiddleware
from ai_backend.api.routers import (
    chat_router,
    concepts_router,
    health_router,
    scan_router,
)
from ai_backend.application.chat_service import ChatService
from ai_backend.application.concept_ingestion_service import ConceptIngestionService
from ai_backend.application.scan_service import ScanService
from ai_backend.infra.market_data import CafefNewsSource, VnstockPriceSource
from ai_backend.infra.notify.console_notifier import ConsoleNotifier
from ai_backend.infra.scheduler import start_scan_scheduler, stop_scan_scheduler
from ai_backend.infra.storage import (
    PgMemoryStore,
    PgPriceHistoryStore,
    PgWatchlistStore,
)
from ai_backend.infra.storage.pg_db import connect
from ai_backend.shared.logging import get_logger, setup_logging
from ai_backend.shared.settings import ai_settings
from common.settings import settings

setup_logging(ai_settings.log_level)
logger = get_logger("ai_backend.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Quản lý vòng đời khởi động và dừng của AI Backend."""
    logger.info(
        f"Khởi động AI Backend Microservice tại http://{ai_settings.host}:{ai_settings.port} "
        f"[LLM={ai_settings.llm_backend}, Qdrant={ai_settings.qdrant_host}:{ai_settings.qdrant_port}]"
    )

    # 1. PostgreSQL: kiểm tra kết nối và tạo bảng ngay khi khởi động
    connect().close()
    logger.info("AI Backend kết nối PostgreSQL")

    # 2. Qdrant: đảm bảo collection bộ nhớ; gợi ý nạp dữ liệu khái niệm nếu collection còn trống
    from ai_backend.infra.storage.long_term_memory import _ensure_collection, get_qdrant_client

    q_client = get_qdrant_client(url=ai_settings.qdrant_url)
    _ensure_collection(q_client, ai_settings.qdrant_collection or "portfolio_watch_memory")
    concept_coll = getattr(ai_settings, "concept_collection", "stock_concepts")
    if not q_client.collection_exists(concept_coll) or q_client.count(concept_coll).count == 0:
        logger.info(
            f"Collection khái niệm '{concept_coll}' chưa có dữ liệu. Gọi POST /v1/concepts/ingest với multipart file .md."
        )

    # 3. MinIO: khởi tạo store ảnh biểu đồ (None nếu chart_backend != minio)
    from common.storage import get_chart_store
    store = get_chart_store()
    if store is not None and not store.is_connected():
        logger.info(f"MinIO chưa sẵn sàng, lưu ảnh biểu đồ tại {ai_settings.charts_dir}")

    price_source = VnstockPriceSource()
    news_source = CafefNewsSource()
    history_store = PgPriceHistoryStore()
    memory_store = PgMemoryStore()
    watchlist_store = PgWatchlistStore()

    # Tạo một lần lúc khởi động, router lấy lại qua request.app.state
    app.state.chat_service = ChatService(
        price_source=price_source,
        news_source=news_source,
        history_store=history_store,
        memory_store=memory_store,
        watchlist_store=watchlist_store,
    )
    scanner = ScanService(
        price_source=price_source,
        news_source=news_source,
        history_store=history_store,
        memory_store=memory_store,
        watchlist_store=watchlist_store,
        notifier=ConsoleNotifier(memory_store, user_id="default"),
    )
    app.state.scan_service = scanner
    app.state.concept_ingestion_service = ConceptIngestionService(client=q_client)

    # 4. Job nền: quét mọi mã trong watchlist của mọi user theo chu kỳ config
    def _scan_watchlist_job() -> None:
        items = watchlist_store.list_all()
        triggered = 0
        for item in items:
            try:
                # Job nền là điểm vào riêng (không qua web) → sinh request_id 1 lần ở đây, truyền xuyên suốt
                out = scanner.scan(
                    symbol=[item.symbol],
                    user_id=item.user_id,
                    request_id=f"scan-job-{uuid4().hex}",
                    threshold_pct=item.threshold_pct,
                )
                triggered += sum(1 for a in out.alerts if a.triggered)
            except Exception as exc:
                logger.warning(f"Quét định kỳ lỗi mã {item.symbol} (user={item.user_id}): {exc}")
        logger.info(f"Quét định kỳ xong {len(items)} mã, {triggered} cảnh báo vượt ngưỡng")

    scheduler = start_scan_scheduler(_scan_watchlist_job, interval_minutes=settings.scan_interval_minutes)

    yield
    stop_scan_scheduler(scheduler)
    logger.info("Dừng AI Backend Microservice.")


# Khởi tạo ứng dụng FastAPI AI Backend
app = FastAPI(
    title=ai_settings.app_name or "VN Stock Swarm AI",
    version=ai_settings.version or "0.0.0",
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
app.include_router(chat_router)
app.include_router(scan_router)
app.include_router(concepts_router)


if __name__ == "__main__":
    import uvicorn

    logger.info(f"AI Service chạy trên http://{ai_settings.host}:{ai_settings.port}")
    uvicorn.run(
        "ai_backend.main:app",
        host=ai_settings.host,
        port=ai_settings.port,
        reload=False,
    )
