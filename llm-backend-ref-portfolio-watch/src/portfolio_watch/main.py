from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.portfolio_watch.api.routers.approvals import router as approvals_router
from src.portfolio_watch.api.routers.chat import router as chat_router
from src.portfolio_watch.api.routers.scan import router as scan_router
from src.portfolio_watch.api.routers.watchlist import router as watchlist_router
from src.portfolio_watch.shared.logging import get_logger, setup_logging
from src.portfolio_watch.shared.settings import settings

setup_logging(settings.log_level)
logger = get_logger(__name__)


def resolve_web_dir() -> Path:
    """Tìm thư mục web/ — local editable, Docker /app/web, hoặc cwd."""
    here = Path(__file__).resolve()
    candidates = (
        here.parents[2] / "web",  # .../llm-backend-ref/web hoặc /app/web (editable)
        Path("/app/web"),  # Docker layout tường minh
        Path.cwd() / "web",
    )
    for cand in candidates:
        if cand.is_dir() and (cand / "index.html").is_file():
            return cand
    return candidates[0]


# llm-backend-ref/web — cùng origin với API khi demo (1 URL)
WEB_DIR = resolve_web_dir()

app = FastAPI(title=settings.app_name, version="0.1.0")

# Dev: web/ (file:// hoặc static server khác origin) gọi API trực tiếp
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


# Mount sau API routes — `/` phục vụ index.html; `/app.js`, `/style.css` cùng host
if WEB_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="web")
    logger.info("static web mounted from %s", WEB_DIR)
else:
    logger.warning("web/ not found at %s — skip static mount", WEB_DIR)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.portfolio_watch.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )
