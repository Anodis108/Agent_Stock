"""NewsAgent — ReAct: chọn từ khóa → fetch tin → đủ chưa → lọc tin liên quan.

LLM được inject qua `NewsAgentBrain` để unit test không cần gọi model thật.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol

from src.portfolio_watch.domain.ports import NewsItem, NewsSource

MAX_STEPS = 5


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


@dataclass
class HeuristicNewsBrain:
    """Brain đơn giản (không LLM) — đủ cho test / fallback."""

    min_relevant: int = 1
    queries: list[str] = field(default_factory=list)

    def decide(
        self, symbol: str, gathered: list[NewsItem], step: int
    ) -> NewsReactAction:
        relevant_so_far = self.filter_relevant(symbol, gathered)
        if len(relevant_so_far) >= self.min_relevant:
            return NewsReactAction(kind="finish")
        if self.queries:
            if step >= len(self.queries):
                return NewsReactAction(kind="finish")
            return NewsReactAction(kind="search", query=self.queries[step])
        if step == 0:
            return NewsReactAction(kind="search", query=symbol)
        return NewsReactAction(kind="finish")

    def filter_relevant(self, symbol: str, items: list[NewsItem]) -> list[NewsItem]:
        key = symbol.strip().upper()
        out: list[NewsItem] = []
        for item in items:
            blob = f"{item.title} {item.snippet} {item.symbol or ''}".upper()
            if key and key in blob:
                out.append(item)
        return out


def run_news_agent(
    symbol: str,
    news_source: NewsSource,
    brain: NewsAgentBrain,
    *,
    days: int | None = 7,
    max_steps: int = MAX_STEPS,
) -> NewsAgentResult:
    if not symbol or not symbol.strip():
        return NewsAgentResult(
            symbol=symbol or "",
            items=[],
            tool_calls=0,
            error="symbol rỗng",
        )

    gathered: list[NewsItem] = []
    tool_calls = 0
    last_error: str | None = None

    try:
        for step in range(max_steps):
            action = brain.decide(symbol, gathered, step)
            if action.kind == "finish":
                break
            if action.kind != "search":
                break

            query = action.query or symbol
            tool_calls += 1
            try:
                batch = news_source.fetch_news(symbol, query=query, days=days)
            except Exception as exc:  # noqa: BLE001
                msg = str(exc)
                last_error = (
                    msg
                    if "không lấy được tin" in msg.lower()
                    else f"không lấy được tin: {exc}"
                )
                break
            gathered.extend(batch or [])

        filtered = brain.filter_relevant(symbol, gathered)
        return NewsAgentResult(
            symbol=symbol,
            items=filtered,
            tool_calls=tool_calls,
            error=last_error,
        )
    except Exception as exc:  # noqa: BLE001
        filtered: list[NewsItem] = []
        try:
            filtered = brain.filter_relevant(symbol, gathered)
        except Exception:  # noqa: BLE001
            filtered = []
        msg = str(exc)
        err = (
            msg
            if "không lấy được tin" in msg.lower()
            else f"không lấy được tin: {exc}"
        )
        return NewsAgentResult(
            symbol=symbol,
            items=filtered,
            tool_calls=tool_calls,
            error=err,
        )
