"""Chat service — JSON chat và SSE stream cùng một graph (start_graph mode=chat).

  POST /v1/chat          → ChatService.process()  (JSON)
  POST /v1/chat/stream* → ChatService.stream_sse() (SSE demo-format)

Cả hai dùng chung request_deps() và start_graph; không gọi LLM trực tiếp ở đây.
"""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import AsyncIterator
from typing import Any

from pydantic import Field

from ai_backend.domain.agents.graph import start_graph
from ai_backend.shared.logging import get_logger
from common.base.base_model import CustomBaseModel
from common.base.base_service import BaseService
from common.domain.ports import (
    MemoryStore,
    NewsSource,
    PriceHistoryStore,
    PriceSource,
    WatchlistStore,
)

logger = get_logger("ai_backend.application.chat_service")


class ChatInput(CustomBaseModel):
    question: str
    user_id: str
    request_id: str


class ChatOutput(CustomBaseModel):
    question: str
    answer: str
    steps: list[dict[str, Any]] = Field(default_factory=list)
    drawed_paths: list[str] = Field(default_factory=list)


def swarm_public_payload(state: dict[str, Any], *, started: float) -> dict[str, Any]:
    """Payload SSE cuối (và web_backend stream) — map state graph → JSON public."""
    # Bước 1: lấy câu trả lời đã synthesis từ checkpoint graph
    final = state["final_answer"]
    # Bước 2: chỉ field client cần + thời gian xử lý
    return {
        "question": final.question,
        "answer": final.answer,
        "drawed_paths": final.drawed_paths,
        "total_duration_s": round(time.perf_counter() - started, 3),
    }


class ChatService(BaseService):
    """Hỏi-đáp: inject port rồi gọi graph mode=chat (JSON hoặc SSE)."""

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
        """Bước 0: gói port inject vào graph chat."""
        return {
            "price_source": self.price_source,
            "news_source": self.news_source,
            "history_store": self.history_store,
            "memory_store": self.memory_store,
            "watchlist_store": self.watchlist_store,
        }

    async def _run_chat_graph(
        self,
        question: str,
        *,
        user_id: str,
        request_id: str,
        request_deps: dict[str, Any] | None = None,
    ) -> AsyncIterator[tuple[str, Any]]:
        """Chung cho process + stream_sse: chạy LangGraph chat và forward event."""
        # Bước 1: deps từ service hoặc caller truyền vào (request_deps)
        deps = self.request_deps() if request_deps is None else request_deps
        # Bước 2: stream (kind, payload) — token | result | …
        async for item in start_graph(
            "chat", question, deps, user_id=user_id, request_id=request_id
        ):
            yield item

    def process(self, inputs: ChatInput) -> ChatOutput:
        """JSON một lần: chạy graph tới result → ChatOutput (không stream token)."""
        # Bước 1: chuẩn hóa input
        question = inputs.question.strip()
        logger.info(
            "ChatService.process: q='%s' user='%s' req_id='%s'",
            question[:50],
            inputs.user_id,
            inputs.request_id,
        )

        async def _collect() -> Any:
            # Bước 2: lắng nghe graph
            result = None
            async for kind, payload in self._run_chat_graph(
                question, user_id=inputs.user_id, request_id=inputs.request_id
            ):
                if kind == "result":
                    result = payload
            # Bước 3: bắt buộc có result (vòng lặp trên đã drain generator → memory sau result chạy xong)
            if result is None:
                raise RuntimeError("start_graph không yield result")
            return result

        # Bước 4: route FastAPI sync — chạy coroutine trong event loop tạm
        final = asyncio.run(_collect())["final_answer"]
        # Bước 5: map sang DTO API (không gửi token từng mảnh)
        return ChatOutput(
            question=question,
            answer=final.answer,
            drawed_paths=final.drawed_paths,
        )

    async def stream_sse(
        self,
        question: str,
        *,
        user_id: str,
        request_id: str,
        request_deps: dict[str, Any] | None = None,
    ) -> AsyncIterator[str]:
        """SSE: token → complete → [DONE]; lỗi → một event error."""

        def _sse_data(payload: dict[str, Any] | str) -> str:
            """Bước phụ: đóng gói một dòng SSE (`data: …\\n\\n`)."""
            if isinstance(payload, str):
                return f"data: {payload}\n\n"
            return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

        def _token_text(chunk: Any) -> str:
            """Bước phụ: graph chunk → text hiển thị."""
            if isinstance(chunk, str):
                return chunk
            if isinstance(chunk, dict) and "delta" in chunk:
                return str(chunk["delta"])
            return str(chunk)

        # Bước 1: chuẩn bị — đo thời gian + câu hỏi
        started = time.perf_counter()
        q = question.strip()
        try:
            # Bước 2: cùng graph với process, nhưng xử lý từng event khi tới
            async for kind, payload in self._run_chat_graph(
                q,
                user_id=user_id,
                request_id=request_id,
                request_deps=request_deps,
            ):
                # Bước 3a: token — client ghép thành câu trả lời đang gõ
                if kind == "token":
                    yield _sse_data({"token": _token_text(payload)})
                # Bước 3b: result — một JSON đủ câu trả lời + metadata
                elif kind == "result":
                    yield _sse_data(
                        {
                            **swarm_public_payload(payload, started=started),
                            "request_id": request_id,
                            "complete": True,
                        }
                    )
            # Bước 4: báo hết stream (sau khi generator graph kết thúc)
            yield _sse_data("[DONE]")
        except Exception as exc:  # noqa: BLE001
            # Bước 5 (nhánh lỗi): vẫn trả SSE để client parse, không đứt im lặng
            yield _sse_data({"error": str(exc)})
