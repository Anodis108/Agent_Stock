"""Backward compatibility redirect to backend.infra.llm.service."""

from __future__ import annotations

from backend.infra.llm.service import app, health

__all__ = ["app", "health"]

if __name__ == "__main__":
    import uvicorn
    from backend.shared.logging import get_logger
    from backend.shared.settings import settings

    logger = get_logger(__name__)
    port = settings.ai_api_port
    host = settings.ai_api_host
    logger.info("AI service on http://%s:%s", host, port)
    uvicorn.run(
        "backend.infra.llm.service:app",
        host=host,
        port=port,
        reload=False,
    )
