"""Web API Routers (cổng 8000)."""

from __future__ import annotations

from backend.api.routers.web import (
    approvals,
    chat,
    hitl,
    market,
    portfolio,
    scan,
    sessions,
    watchlist,
)

__all__ = [
    "approvals",
    "chat",
    "hitl",
    "market",
    "portfolio",
    "scan",
    "sessions",
    "watchlist",
]
