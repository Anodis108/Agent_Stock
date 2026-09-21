"""NewsState — TypedDict cho graph (Phase 13)."""

from __future__ import annotations

from typing import TypedDict

from src.portfolio_watch.agents.news_agent.schemas import NewsAgentResult
from src.portfolio_watch.domain.ports import NewsItem


class NewsState(TypedDict, total=False):
    symbol: str
    gathered: list[NewsItem]
    result: NewsAgentResult
