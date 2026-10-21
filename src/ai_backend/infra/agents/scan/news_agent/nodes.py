"""NewsAgent — ReAct: chọn từ khóa → fetch tin → lọc tin liên quan."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from ai_backend.infra.agents.scan.news_agent.schemas import (
    NewsAgentBrain,
    NewsAgentResult,
    NewsReactAction,
    NewsReactOutput,
)
from ai_backend.infra.agents.scan.news_agent.tools import fetch_cafef_news
from common.domain.ports import NewsItem, NewsSource
from ai_backend.infra.llm.params import DETERMINISTIC
from ai_backend.infra.llm.prompt_registry import registry
from ai_backend.infra.llm.structured import call_llm_structured

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


from ai_backend.infra.monitoring.tracing import agent_step

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

# ==============================================================================
# Graph node (Hierarchical Swarm)
# ==============================================================================

import time

from langchain_core.runnables import RunnableConfig

from ai_backend.infra.agents.scan.news_agent.schemas import NewsAgentBrain
from ai_backend.infra.agents.events import emit_agent_event, graph_deps, run_per_symbol, target_symbols
from ai_backend.infra.monitoring.tracing import agent_span
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # chỉ type hint — graph.state import ngược các agent
    from ai_backend.infra.agents.state import SwarmState


def news_node(
    sym: str,
    news_source: NewsSource,
    news_brain: NewsAgentBrain | None = None,
    days: int | None = 7,
    turn: str = "",
) -> NewsAgentResult:
    """Trích xuất tin tức CafeF cho một mã cổ phiếu cụ thể."""
    t0 = time.perf_counter()
    emit_agent_event("node_start", {"node": "news_agent", "symbol": sym, "timestamp": time.time()})
    with agent_span(turn, "news_agent", input=sym) as box:
        n = run_news_agent(
            sym,
            news_source,
            news_brain or default_news_brain(),
            days=days,
            turn=turn,
        )
        box["output"] = {
            "symbol": sym,
            "items": len(n.items or []),
            "error": n.error,
        }
        dur = round(time.perf_counter() - t0, 3)
        emit_agent_event("node_finish", {"node": "news_agent", "symbol": sym, "duration_s": dur, "duration_ms": int(dur * 1000)})
        return n


def news_agent_node(state: SwarmState, config: RunnableConfig) -> dict[str, Any]:
    """Worker tin tức (ReAct): lấy tin CafeF. Chat chỉ cần tin để eval thì chỉ lấy cho mã chính."""
    cfg = graph_deps.get()
    symbols = target_symbols(state)
    routing = state.get("routing")
    if state.get("mode") == "chat" and routing and "news" not in [a.lower() for a in (routing.agents_to_call or [])]:
        symbols = [state["symbol"]] if state.get("symbol") else symbols[:1]
    news_list = run_per_symbol(
        news_node, symbols, cfg["news_source"], cfg.get("news_brain"), cfg.get("news_days", 7), state.get("turn") or ""
    )
    main = (state.get("symbol") or "").upper()
    news = next((n for n in news_list if (n.symbol or "").upper() == main), news_list[0] if news_list else None)
    return {"news": news, "news_list": news_list, "completed": ["news_agent"]}
