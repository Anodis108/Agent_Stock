"""Backward compatibility redirect to ai_backend.main or backend.ai_main."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from ai_backend.api.routers import v1

app = FastAPI(
    title="AI Backend Microservice (v1)",
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

app.include_router(v1.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "ai"}


__all__ = ["app", "health"]


if __name__ == "__main__":
    import uvicorn
    from common.logging import get_logger
    from common.settings import settings

    logger = get_logger(__name__)
    port = settings.ai_api_port
    host = settings.ai_api_host
    logger.info("AI service on http://%s:%s", host, port)
    uvicorn.run(
        "ai_backend.main:app",
        host=host,
        port=port,
        reload=False,
    )
