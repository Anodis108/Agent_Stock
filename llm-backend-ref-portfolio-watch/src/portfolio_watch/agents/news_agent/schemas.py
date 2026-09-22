"""I/O news_agent — ReAct search/finish + Pydantic schemas."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

from src.portfolio_watch.domain.ports import NewsItem
from src.portfolio_watch.shared.schemas import NewsReactOutput


@dataclass(slots=True)
class NewsReactAction:
    kind: Literal["search", "finish"]
    query: str | None = None


class NewsAgentBrain(Protocol):
    def decide(
        self, symbol: str, gathered: list[NewsItem], step: int
    ) -> NewsReactAction:
        """Chọn search (kèm query) hoặc finish khi đã đủ tin."""
        ...

    def filter_relevant(self, symbol: str, items: list[NewsItem]) -> list[NewsItem]:
        """Giữ tin thực sự liên quan tới mã."""
        ...


@dataclass(slots=True)
class NewsAgentResult:
    symbol: str
    items: list[NewsItem]
    tool_calls: int = 0
    error: str | None = None


__all__ = [
    "NewsAgentBrain",
    "NewsAgentResult",
    "NewsReactAction",
    "NewsReactOutput",
]
