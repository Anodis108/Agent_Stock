"""Chat service — use-case chat: gọi LangGraph (start_graph mode=chat) và map kết quả.

Luồng tổng quan:
  API (chat.py) → ChatService.process()
    → start_graph (domain/agents/graph.py, mode=chat)
    → supervisor / agents (giá, tin, RAG, vẽ chart, …) → state checkpoint
    → ChatOutput (JSON). SSE token: infra/llm/chat_stream.swarm_sse (dùng request_deps()).

Kế thừa BaseService; không chứa logic agent — chỉ inject port + cấu hình memory/news.
"""

from __future__ import annotations

import asyncio
from typing import Any
from pydantic import Field

from common.base.base_model import CustomBaseModel
from common.base.base_service import BaseService
from common.domain.ports import MemoryStore, NewsSource, PriceHistoryStore, PriceSource, WatchlistStore
from ai_backend.shared.logging import get_logger

from ai_backend.domain.agents.graph import start_graph

logger = get_logger("ai_backend.application.chat_service")


class ChatInput(CustomBaseModel):
    """Input payload cho chat service."""
    question: str
    user_id: str = "default"
    request_id: str | None = None


class ChatOutput(CustomBaseModel):
    """Output payload từ chat service."""
    question: str
    answer: str
    rewritten_symbol: list[str] = Field(default_factory=list)
    routing: str = "general"
    steps: list[dict[str, Any]] = Field(default_factory=list)
    chart_path: str | None = None
    error: str | None = None


class ChatService(BaseService):
    """Service hỏi-đáp: inject port rồi gọi graph mode=chat."""

    def __init__(
        self,
        *,
        price_source: PriceSource | None = None,
        news_source: NewsSource | None = None,
        history_store: PriceHistoryStore | None = None,
        memory_store: MemoryStore | None = None,
        watchlist_store: WatchlistStore | None = None,
    ) -> None:
        self.price_source = price_source
        self.news_source = news_source
        self.history_store = history_store
        self.memory_store = memory_store
        self.watchlist_store = watchlist_store

    def request_deps(self) -> dict[str, Any]:
        """Port inject vào graph (context của LangGraph) — process() và SSE (/v1/chat/stream-sse) dùng chung."""
        return {
            "price_source": self.price_source,
            "news_source": self.news_source,
            "history_store": self.history_store,
            "memory_store": self.memory_store,
            "watchlist_store": self.watchlist_store,
        }

    def process(self, inputs: ChatInput) -> ChatOutput:
        """Hỏi-đáp đồng bộ qua graph mode=chat."""
        question = inputs.question.strip()
        req_id = inputs.request_id
        logger.info(f"ChatService.process: q='{question[:50]}' user='{inputs.user_id}' req_id='{req_id}'")

        # Bước 1–2 — Inject port vào graph (request_deps); memory window đọc trong node (settings).
        async def _run() -> Any:
            async for kind, payload in start_graph(
                "chat", question, self.request_deps(), user_id=inputs.user_id, request_id=req_id
            ):
                if kind == "result":
                    return payload
            raise RuntimeError("start_graph không yield result")

        state = asyncio.run(_run())
        rewritten = state["rewritten"]
        guard = state["guardrail_result"]
        if rewritten is not None:
            routing = str(rewritten.intent)
        elif guard is None:
            routing = "empty"
        elif guard.category == "greeting":
            routing = "greeting"
        else:
            routing = "guardrail"
        chart = state["chart_result"]
        chart_path = chart.url if chart is not None and chart.success else None

        return ChatOutput(
            question=question,
            answer=state["answer"] or "",
            rewritten_symbol=list(rewritten.symbols) if rewritten is not None else [],
            routing=routing,
            chart_path=chart_path,
            error=state["error"],
        )
