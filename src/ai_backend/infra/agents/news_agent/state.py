"""NewsState — TypedDict cho graph (Phase 13)."""

from __future__ import annotations

from typing import TypedDict

from ai_backend.infra.agents.news_agent.schemas import NewsAgentResult
from common.domain.ports import NewsItem


class NewsState(TypedDict, total=False):
    symbol: str
    gathered: list[NewsItem]
    result: NewsAgentResult
