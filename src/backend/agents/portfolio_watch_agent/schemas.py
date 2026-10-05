"""Schemas for PortfolioWatchAgent — Data contracts for Portfolio & Watchlist."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from backend.domain.entities import WatchlistItem


@dataclass(slots=True)
class PortfolioWatchAgentResult:
    """Kết quả xử lý từ PortfolioWatchAgent."""
    user_id: str
    intent: Literal["portfolio", "watchlist", "all"]
    portfolio_summary: Any | None = None
    watchlist_items: list[WatchlistItem] = field(default_factory=list)
    formatted_markdown: str = ""
    error: str | None = None
