"""Canonical app entrypoint and backward-compatibility facade for backend.api.main."""

from __future__ import annotations

from backend.api.main import *
from backend.api.main import (
    AiClientError,
    DEFAULT_THRESHOLD,
    DEFAULT_WATCHLIST,
    _CHARTS_DIR,
    _FRONTEND_DIR,
    ai_chat,
    ai_scan,
    app,
    store,
)

if __name__ == "__main__":
    import os
    import uvicorn
    from backend.shared.settings import settings

    host = os.environ.get("API_HOST", settings.api_host or "127.0.0.1")
    port = int(os.environ.get("API_PORT", settings.api_port or 8000))
    uvicorn.run("backend.api.main:app", host=host, port=port, reload=False)
