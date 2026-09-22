"""NewsAgent — ReAct: chọn từ khóa → fetch tin → lọc tin liên quan."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from src.portfolio_watch.agents.news_agent.schemas import (
    NewsAgentBrain,
    NewsAgentResult,
    NewsReactAction,
    NewsReactOutput,
)
from src.portfolio_watch.agents.news_agent.tools import fetch_cafef_news
from src.portfolio_watch.domain.ports import NewsItem, NewsSource
from src.portfolio_watch.infra.llm.params import DETERMINISTIC
from src.portfolio_watch.infra.llm.prompt_registry import registry
from src.portfolio_watch.infra.llm.structured import call_llm_structured

MAX_STEPS = 5


def _filter_by_symbol(symbol: str, items: list[NewsItem]) -> list[NewsItem]:
    key = symbol.strip().upper()
    out: list[NewsItem] = []
    for item in items:
        blob = f"{item.title} {item.snippet} {item.symbol or ''}".upper()
        if key and key in blob:
            out.append(item)
    return out


def _gathered_summary(gathered: list[NewsItem], limit: int = 8) -> str:
    if not gathered:
        return "(chưa có tin)"
    parts = []
    for item in gathered[:limit]:
        title = (item.title or "").strip()
        if title:
            parts.append(title)
    return "; ".join(parts) if parts else "(chưa có tin)"


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
        return _filter_by_symbol(symbol, items)


class LlmNewsBrain:
    """LLM ReAct decide qua registry `news_agent_react` + structured output; filter = heuristic."""

    def __init__(
        self,
        *,
        chat_fn: Callable[..., str] | None = None,
        chat_parsed_fn: Callable[..., Any] | None = None,
        prompt_version: str | int = "production",
        days: int = 7,
    ) -> None:
        self._chat_fn = chat_fn
        self._chat_parsed_fn = chat_parsed_fn
        self._prompt_version = prompt_version
        self.days = days

    def decide(
        self, symbol: str, gathered: list[NewsItem], step: int
    ) -> NewsReactAction:
        prompt_text = registry().render(
            "news_agent_react",
            version=self._prompt_version,
            symbol=symbol or "",
            days=str(self.days),
            step=str(step),
            gathered_summary=_gathered_summary(gathered),
        )
        messages = [{"role": "user", "content": prompt_text}]
        try:
            output = call_llm_structured(
                messages,
                NewsReactOutput,
                chat_fn=self._chat_fn,
                chat_parsed_fn=self._chat_parsed_fn,
                params=DETERMINISTIC,
                max_retries=1,
            )
            return NewsReactAction(
                kind=output.kind,
                query=output.query or (symbol if output.kind == "search" else None),
            )
        except Exception:
            # inner schema fallback: finish ReAct safely
            return NewsReactAction(kind="finish", query=None)

    def filter_relevant(self, symbol: str, items: list[NewsItem]) -> list[NewsItem]:
        return _filter_by_symbol(symbol, items)


_DEFAULT_NEWS_BRAIN_FACTORY: Callable[[], NewsAgentBrain] = LlmNewsBrain


def default_news_brain() -> NewsAgentBrain:
    return _DEFAULT_NEWS_BRAIN_FACTORY()


from src.portfolio_watch.infra.monitoring.tracing import agent_step

def run_news_agent(
    symbol: str,
    news_source: NewsSource,
    brain: NewsAgentBrain | None = None,
    *,
    days: int | None = 7,
    max_steps: int = MAX_STEPS,
    turn: str = "",
) -> NewsAgentResult:
    if not symbol or not symbol.strip():
        return NewsAgentResult(
            symbol=symbol or "",
            items=[],
            tool_calls=0,
            error="symbol rỗng",
        )

    agent = brain or default_news_brain()
    if isinstance(agent, LlmNewsBrain):
        agent.days = int(days) if days is not None else 7

    gathered: list[NewsItem] = []
    tool_calls = 0
    last_error: str | None = None

    try:
        for step in range(max_steps):
            with agent_step(
                turn,
                "news_agent",
                f"react_turn_{step}",
                input={"step": step, "symbol": symbol, "gathered": len(gathered)},
            ) as box:
                action = agent.decide(symbol, gathered, step)
                box["output"] = {"kind": action.kind, "query": action.query}
            if action.kind == "finish":
                break
            if action.kind != "search":
                break

            query = action.query or symbol
            tool_calls += 1
            try:
                with agent_step(
                    turn, "news_agent", "fetch_news", input={"query": query}
                ) as box:
                    batch = fetch_cafef_news(
                        news_source, symbol, query, days=days
                    )
                    box["output"] = {"items": len(batch)}
            except Exception as exc:  # noqa: BLE001
                msg = str(exc)
                last_error = (
                    msg
                    if "không lấy được tin" in msg.lower()
                    else f"không lấy được tin: {exc}"
                )
                break
            gathered.extend(batch)

        filtered = agent.filter_relevant(symbol, gathered)
        return NewsAgentResult(
            symbol=symbol,
            items=filtered,
            tool_calls=tool_calls,
            error=last_error,
        )
    except Exception as exc:  # noqa: BLE001
        filtered: list[NewsItem] = []
        try:
            filtered = agent.filter_relevant(symbol, gathered)
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
