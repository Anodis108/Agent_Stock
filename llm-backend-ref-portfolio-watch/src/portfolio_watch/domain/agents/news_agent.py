"""NewsAgent — ReAct: chọn từ khóa → fetch tin → đủ chưa → lọc tin liên quan.

Phase 8: mặc định dùng LLM qua Prompt Registry (`news_agent_react`) +
`infra/llm.completion.chat` cho bước `decide`. `filter_relevant` giữ heuristic
(symbol trong title/snippet) — prompt JSON chỉ trả search/finish.
`HeuristicNewsBrain` giữ cho unit test / inject.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Literal, Protocol

from src.portfolio_watch.domain.ports import NewsItem, NewsSource
from src.portfolio_watch.infra.llm.completion import chat
from src.portfolio_watch.infra.llm.params import DETERMINISTIC
from src.portfolio_watch.infra.llm.prompt_registry import registry

MAX_STEPS = 5
_JSON_OBJ_RE = re.compile(r"\{.*\}", re.DOTALL)


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


def _parse_react_action(raw: str, *, symbol: str) -> NewsReactAction:
    text = (raw or "").strip()
    match = _JSON_OBJ_RE.search(text)
    payload = match.group(0) if match else text
    data = json.loads(payload)
    if not isinstance(data, dict):
        raise ValueError("NewsAgent LLM không trả JSON object")
    kind = str(data.get("kind", "")).strip().lower()
    query = data.get("query")
    query_s = None if query is None else str(query).strip() or None
    if kind == "finish":
        return NewsReactAction(kind="finish", query=None)
    if kind == "search":
        return NewsReactAction(kind="search", query=query_s or symbol)
    raise ValueError(f"kind không hợp lệ từ LLM: {kind!r}")


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
    """LLM ReAct decide qua registry `news_agent_react`; filter = heuristic."""

    def __init__(
        self,
        *,
        chat_fn: Callable[..., str] | None = None,
        prompt_version: str | int = "production",
        days: int = 7,
    ) -> None:
        self._chat_fn = chat_fn or chat
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
        raw = self._chat_fn(
            [{"role": "user", "content": prompt_text}],
            DETERMINISTIC,
        )
        return _parse_react_action(raw, symbol=symbol)

    def filter_relevant(self, symbol: str, items: list[NewsItem]) -> list[NewsItem]:
        return _filter_by_symbol(symbol, items)


# Production mặc định = LLM; pytest monkeypatch → Heuristic (conftest).
_DEFAULT_NEWS_BRAIN_FACTORY: Callable[[], NewsAgentBrain] = LlmNewsBrain


def default_news_brain() -> NewsAgentBrain:
    return _DEFAULT_NEWS_BRAIN_FACTORY()


def run_news_agent(
    symbol: str,
    news_source: NewsSource,
    brain: NewsAgentBrain | None = None,
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

    agent = brain or default_news_brain()
    if isinstance(agent, LlmNewsBrain):
        agent.days = int(days) if days is not None else 7

    gathered: list[NewsItem] = []
    tool_calls = 0
    last_error: str | None = None

    try:
        for step in range(max_steps):
            action = agent.decide(symbol, gathered, step)
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
