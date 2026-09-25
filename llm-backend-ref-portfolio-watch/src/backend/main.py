from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routers.approvals import router as approvals_router
from backend.api.routers.chat import router as chat_router
from backend.api.routers.market import (
    alias_router as alias_market_router,
    direct_router as direct_market_router,
    router as market_router,
)
from backend.api.routers.hitl import (
    alias_router as alias_hitl_router,
    direct_router as direct_hitl_router,
    router as hitl_router,
)
from backend.api.routers.scan import router as scan_router
from backend.api.routers.sessions import alias_router as alias_sessions_router
from backend.api.routers.sessions import router as sessions_router
from backend.api.routers.watchlist import router as watchlist_router
from backend.shared.logging import get_logger, setup_logging
from backend.shared.settings import settings

setup_logging(settings.log_level)
logger = get_logger(__name__)

app = FastAPI(title=settings.app_name, version="0.1.0")

# Dev: frontend process (port 5173) gọi API qua CORS — không mount static UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(scan_router)
app.include_router(chat_router)
app.include_router(approvals_router)
app.include_router(watchlist_router)
app.include_router(sessions_router)
app.include_router(alias_sessions_router)
app.include_router(market_router)
app.include_router(alias_market_router)
app.include_router(direct_market_router)
app.include_router(hitl_router)
app.include_router(alias_hitl_router)
app.include_router(direct_hitl_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )
