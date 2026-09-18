from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.portfolio_watch.api.routers.approvals import router as approvals_router
from src.portfolio_watch.api.routers.chat import router as chat_router
from src.portfolio_watch.api.routers.scan import router as scan_router
from src.portfolio_watch.api.routers.watchlist import router as watchlist_router
from src.portfolio_watch.shared.logging import get_logger, setup_logging
from src.portfolio_watch.shared.settings import settings

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


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.portfolio_watch.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )
