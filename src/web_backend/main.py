"""Web Backend Microservice — FastAPI Entrypoint (Cổng 8000).

Cung cấp:
- Cổng tiếp nhận câu hỏi chứng khoán và điều phối Streaming SSE ra Web UI.
- Quản lý danh mục đầu tư (Holdings, NAV, P&L, Alert Thresholds) theo user_id.
- Quản lý danh mục theo dõi (Watchlist) và trạng thái phiên thị trường (Market Watch).
- Ghi nhận đánh giá phản hồi Human-In-The-Loop (HITL) và kiểm duyệt lệnh.
- Phục vụ tĩnh giao diện Frontend Web SPA và biểu đồ kỹ thuật /charts.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from common.logging.logger import get_logger
from web_backend.api.helpers.exception_handler import register_exception_handlers
from web_backend.api.helpers.middlewares import CorrelationIdMiddleware, RequestLoggingMiddleware
from web_backend.api.routers.approvals import router as approvals_router
from web_backend.api.routers.chat import router as chat_router
from web_backend.api.routers.hitl import (
    alias_router as hitl_alias_router,
    direct_router as hitl_direct_router,
    router as hitl_router,
)
from web_backend.api.routers.market import router as market_router
from web_backend.api.routers.portfolio import router as portfolio_router
from web_backend.api.routers.scan import router as scan_router
from web_backend.api.routers.sessions import (
    alias_router as sessions_alias_router,
    router as sessions_router,
)
from web_backend.api.routers.watchlist import router as watchlist_router
from web_backend.infra.ai_client.remote_ai_client import RemoteAiClient
from web_backend.infra.database.connection import get_connection, init_db
from web_backend.shared.settings import web_settings

logger = get_logger("web_backend.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Quản lý vòng đời khởi động và dừng của Web Backend."""
    logger.info(f"Khởi động Web Backend Microservice tại cổng {web_settings.port}...")
    try:
        conn = get_connection()
        init_db(conn)
        conn.close()
        logger.info("Khởi tạo cơ sở dữ liệu Web Backend thành công.")
    except Exception as exc:
        logger.warning(f"Lỗi khởi tạo cơ sở dữ liệu khi khởi động: {exc}")
    yield
    logger.info("Dừng Web Backend Microservice.")


# Khởi tạo ứng dụng FastAPI chính
app = FastAPI(
    title=web_settings.app_name,
    version=web_settings.version,
    description="Web Gateway Microservice phục vụ người dùng và giao tiếp AI Swarm qua HTTP.",
    lifespan=lifespan,
)

# 1. Đăng ký Middlewares
app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=web_settings.cors_origins if web_settings.cors_origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Đăng ký Global Exception Handlers
register_exception_handlers(app)


# 3. Health Endpoint
@app.get("/health", tags=["system"])
def health_check() -> dict[str, Any]:
    """Kiểm tra trạng thái hoạt động của Web Backend và độ sẵn sàng của AI Backend."""
    ai_client = RemoteAiClient(base_url=web_settings.ai_base_url)
    ai_health = ai_client.check_health()

    return {
        "status": "ok",
        "service": "web_backend",
        "port": web_settings.port,
        "version": web_settings.version,
        "ai_backend": ai_health,
    }


# 4. Đăng ký toàn bộ 8 Router Web
app.include_router(chat_router)
app.include_router(portfolio_router)
app.include_router(watchlist_router)
app.include_router(sessions_router)
app.include_router(sessions_alias_router)
app.include_router(hitl_router)
app.include_router(hitl_alias_router)
app.include_router(hitl_direct_router)
app.include_router(market_router)
app.include_router(approvals_router)
app.include_router(scan_router)


# 5. Phục vụ biểu đồ kỹ thuật tĩnh (/charts)
charts_path = Path(web_settings.charts_dir)
if not charts_path.is_dir():
    # Tìm fallback thư mục charts
    candidates = [
        Path.cwd() / "resources" / "data" / "charts",
        Path.cwd() / "data" / "charts",
        Path(__file__).resolve().parents[2] / "resources" / "data" / "charts",
    ]
    for c in candidates:
        if c.is_dir():
            charts_path = c
            break

charts_path.mkdir(parents=True, exist_ok=True)
app.mount("/charts", StaticFiles(directory=str(charts_path)), name="charts")


# 6. Phục vụ giao diện Frontend Web SPA
frontend_dir = None
for candidate in [
    Path.cwd() / "frontend" / "dist",
    Path.cwd() / "frontend",
    Path.cwd() / "src" / "frontend",
    Path(__file__).resolve().parents[1] / "frontend",
    Path(__file__).resolve().parents[2] / "src" / "frontend",
    Path(__file__).resolve().parents[2] / "frontend",
    Path("/app/frontend"),
]:
    if candidate.is_dir() and (candidate / "index.html").is_file():
        frontend_dir = candidate
        break

if frontend_dir is not None:
    @app.get("/", include_in_schema=False)
    def serve_frontend_index():
        return FileResponse(frontend_dir / "index.html")

    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
else:
    @app.get("/", include_in_schema=False)
    def default_root_page():
        return {
            "message": "VN Stock Swarm Web Gateway Microservice is running",
            "docs": "/docs",
            "health": "/health",
        }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "web_backend.main:app",
        host=web_settings.host,
        port=web_settings.port,
        reload=False,
    )
