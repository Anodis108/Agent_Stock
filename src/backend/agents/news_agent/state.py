"""NewsState — TypedDict cho graph (Phase 13)."""

from __future__ import annotations

from typing import TypedDict

from backend.agents.news_agent.schemas import NewsAgentResult
from backend.domain.ports import NewsItem


class NewsState(TypedDict, total=False):
    symbol: str
    gathered: list[NewsItem]
    result: NewsAgentResult
