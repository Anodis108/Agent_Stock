"""AI service process — port mặc định 8001, không mount static UI.

    python -m backend.ai_main
    # hoặc: docker compose up ai
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routers.v1 import router as v1_router
from backend.shared.logging import get_logger, setup_logging
from backend.shared.settings import settings

setup_logging(settings.log_level)
logger = get_logger(__name__)

app = FastAPI(
    title=f"{settings.app_name} (AI)",
    version="0.1.0",
    description="AI multi-agent service — /v1/chat, /v1/scan",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(v1_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "ai"}


if __name__ == "__main__":
    import uvicorn

    port = settings.ai_api_port
    host = settings.ai_api_host
    logger.info("AI service on http://%s:%s", host, port)
    uvicorn.run(
        "backend.ai_main:app",
        host=host,
        port=port,
        reload=False,
    )
