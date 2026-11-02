"""State worker news_agent = WorkerState + artifact NewsAgentResult."""

from __future__ import annotations

from pydantic import BaseModel

from ai_backend.domain.agents.multi_agent.hierarchical import WorkerState
from common.domain.ports import NewsItem


class NewsAgentResult(BaseModel):
    symbol: str
    items: list[NewsItem]
    error: str | None = None


class NewsWorkerState(WorkerState, total=False):
    symbols: list[str]
    news: list[NewsAgentResult]
