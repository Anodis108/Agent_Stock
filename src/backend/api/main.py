"""Backward compatibility redirect to backend.main."""

from __future__ import annotations

from backend.main import *
from backend.main import (
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

__all__ = [
    "app",
    "store",
    "ai_chat",
    "ai_scan",
    "DEFAULT_WATCHLIST",
    "DEFAULT_THRESHOLD",
    "AiClientError",
    "_FRONTEND_DIR",
    "_CHARTS_DIR",
]
