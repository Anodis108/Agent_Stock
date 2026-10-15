"""Swarm Orchestrator service — Điều phối LangGraph Multi-Agent Swarm (thay thế use-case answer_question).

Kế thừa BaseService từ common.base.base_service.
Cung cấp phương thức process() đồng bộ và phương thức stream() phục vụ SSE streaming.
"""

from __future__ import annotations

import re
import uuid
from typing import Any, Callable, Iterator
from pydantic import Field

from common.base.base_model import CustomBaseModel
from common.base.base_service import BaseService
from common.logging.logger import get_logger

logger = get_logger("ai_backend.application.swarm_orchestrator")


class SwarmInput(CustomBaseModel):
    """Input payload cho Swarm Orchestrator."""
    question: str
    user_id: str = "default"
    request_id: str | None = None
    watchlist: list[str] = Field(default_factory=list)
    holdings: list[dict[str, Any]] = Field(default_factory=list)
    news_days: int = 7
    limit: int | None = None
    ttl_minutes: int | float | None = None


class SwarmOutput(CustomBaseModel):
    """Output payload từ Swarm Orchestrator."""
    question: str
    answer: str
    rewritten_symbol: str | None = None
    routing: str = "general"
    steps: list[dict[str, Any]] = Field(default_factory=list)
    chart_path: str | None = None
    source_file: str | None = None
    hitl_used: bool = False
    pending_approvals_created: int = 0
    error: str | None = None


_GREETING_REGEX = re.compile(
    r"^\s*(xin\s+chào|chào\s+bạn|hello|hi|hey|chào\s+bot|alo)\b",
    re.IGNORECASE,
)


def is_greeting(text: str) -> bool:
    """Nhận diện nhanh câu hỏi chào hỏi xã giao."""
    return bool(_GREETING_REGEX.search(text.strip()))


class SwarmOrchestrator(BaseService):
    """Service điều phối LangGraph Swarm Đa Tác Tử."""

    def __init__(
        self,
        *,
        graph_runner: Callable[..., Any] | None = None,
        price_source: Any = None,
        news_source: Any = None,
        history_store: Any = None,
        memory_store: Any = None,
        watchlist_store: Any = None,
    ) -> None:
        self.graph_runner = graph_runner
        self.price_source = price_source
        self.news_source = news_source
        self.history_store = history_store
        self.memory_store = memory_store
        self.watchlist_store = watchlist_store

    def process(self, inputs: SwarmInput) -> SwarmOutput:
        """Xử lý điều phối Swarm hỏi-đáp đồng bộ."""
        q = inputs.question.strip()
        req_id = inputs.request_id or str(uuid.uuid4())
        logger.info(f"SwarmOrchestrator.process: q='{q[:50]}' user='{inputs.user_id}' req_id='{req_id}'")

        # 1. Fast-path chào hỏi (TTFT < 1s, bỏ qua LLM / Swarm)
        if is_greeting(q):
            answer = (
                "Xin chào! Tôi là trợ lý chứng khoán VN Stock Swarm. "
                "Tôi có thể hỗ trợ bạn tra cứu thị giá, tin tức, chỉ báo kỹ thuật RSI/SMA, "
                "vẽ biểu đồ nến và theo dõi danh mục đầu tư."
            )
            steps = [
                {"id": "1", "name": "greeting_fastpath", "status": "done", "detail": "Greeting detected"},
                {"id": "2", "name": "answer_composer", "status": "done", "detail": "Immediate greeting response"},
            ]
            return SwarmOutput(
                question=q,
                answer=answer,
                routing="greeting",
                steps=steps,
            )

        # 2. Nếu có graph runner được inject (Phase 3.4) hoặc legacy graph runner
        if self.graph_runner is not None:
            try:
                wl_store = self.watchlist_store
                if inputs.watchlist and hasattr(wl_store, "upsert"):
                    from common.domain.entities import WatchlistItem
                    for sym in inputs.watchlist:
                        try:
                            wl_store.upsert(WatchlistItem(symbol=sym, user_id=inputs.user_id))
                        except Exception:
                            pass

                kwargs: dict[str, Any] = {
                    "user_id": inputs.user_id,
                    "request_id": req_id,
                    "account_holdings": inputs.holdings,
                    "news_days": inputs.news_days,
                }
                if self.price_source is not None:
                    kwargs["price_source"] = self.price_source
                if self.news_source is not None:
                    kwargs["news_source"] = self.news_source
                if self.history_store is not None:
                    kwargs["history_store"] = self.history_store
                if self.memory_store is not None:
                    kwargs["memory_store"] = self.memory_store
                if wl_store is not None:
                    kwargs["watchlist_store"] = wl_store

                res = self.graph_runner(q, **kwargs)
                if isinstance(res, SwarmOutput):
                    return res
                if hasattr(res, "answer"):
                    steps_data = []
                    for s in getattr(res, "steps", []):
                        if hasattr(s, "model_dump"):
                            steps_data.append(s.model_dump())
                        elif hasattr(s, "__dict__"):
                            steps_data.append(dict(s.__dict__))
                        elif isinstance(s, dict):
                            steps_data.append(s)

                    routing_val = "general"
                    routing_obj = getattr(res, "routing", None)
                    if routing_obj:
                        routing_val = str(getattr(routing_obj, "route", routing_obj))

                    symbol_val = None
                    rewritten_obj = getattr(res, "rewritten", None)
                    if rewritten_obj:
                        symbol_val = getattr(rewritten_obj, "symbol", None)

                    return SwarmOutput(
                        question=q,
                        answer=getattr(res, "answer", "") or "",
                        rewritten_symbol=symbol_val,
                        routing=routing_val,
                        steps=steps_data,
                        chart_path=getattr(res, "chart_path", None),
                        source_file=getattr(res, "source_file", None),
                        hitl_used=getattr(res, "hitl_used", False),
                        pending_approvals_created=getattr(res, "pending_approvals_created", 0),
                        error=getattr(res, "error", None),
                    )
            except Exception as exc:
                logger.error(f"Lỗi graph_runner trong SwarmOrchestrator: {exc}", exc_info=True)
                return SwarmOutput(
                    question=q,
                    answer=f"Hệ thống gặp sự cố xử lý câu hỏi: {exc}",
                    routing="error",
                    error=str(exc),
                )

        # 3. Luồng phản hồi tiêu chuẩn độc lập (hỗ trợ kiểm thử 100% offline)
        steps = [
            {"id": "1", "name": "supervisor", "status": "done", "detail": f"Route evaluated for '{q}'"},
            {"id": "2", "name": "answer_composer", "status": "done", "detail": "Response generated"},
        ]
        return SwarmOutput(
            question=q,
            answer=f"Phản hồi từ VN Stock Swarm cho câu hỏi: '{q}'",
            routing="general",
            steps=steps,
        )

    def stream(
        self,
        question: str,
        user_id: str = "default",
        request_id: str | None = None,
        watchlist: list[str] | None = None,
        holdings: list[dict[str, Any]] | None = None,
    ) -> Iterator[tuple[str, dict[str, Any]]]:
        """Tạo luồng sự kiện SSE (event_type, payload) phục vụ streaming ra Web UI."""
        q = (question or "").strip()
        req_id = request_id or str(uuid.uuid4())

        # Fast-path cho câu chào hỏi
        if is_greeting(q):
            yield (
                "node_start",
                {"node": "greeting_fastpath", "input_data": {"question": q, "user_id": user_id}},
            )
            greeting_text = (
                "Xin chào! Tôi là trợ lý chứng khoán VN Stock Swarm. "
                "Bạn có thể tra cứu thị giá, tin tức, chỉ báo kỹ thuật và danh mục đầu tư."
            )
            yield ("token", {"token": greeting_text, "node": "greeting_fastpath", "index": 0})
            yield (
                "node_finish",
                {"node": "greeting_fastpath", "output_data": {"done": True}, "duration_ms": 10},
            )
            yield (
                "complete",
                {
                    "answer": greeting_text,
                    "route": "greeting",
                    "request_id": req_id,
                    "steps": [
                        {"id": "1", "name": "greeting_fastpath", "status": "done"},
                    ],
                },
            )
            return

        # Luồng tiêu chuẩn qua process()
        inp = SwarmInput(
            question=q,
            user_id=user_id,
            request_id=req_id,
            watchlist=watchlist or [],
            holdings=holdings or [],
        )

        yield (
            "node_start",
            {"node": "supervisor", "input_data": {"question": q, "user_id": user_id}},
        )

        output = self.process(inp)

        yield (
            "node_finish",
            {
                "node": "supervisor",
                "output_data": {"route": output.routing, "symbol": output.rewritten_symbol},
            },
        )

        yield (
            "node_start",
            {"node": "answer_composer", "input_data": {"route": output.routing}},
        )

        # Phát token từng từ
        words = output.answer.split(" ")
        for idx, word in enumerate(words):
            token = word + (" " if idx < len(words) - 1 else "")
            yield (
                "token",
                {"token": token, "node": "answer_composer", "index": idx},
            )

        yield (
            "node_finish",
            {"node": "answer_composer", "duration_ms": 50},
        )

        yield (
            "complete",
            {
                "answer": output.answer,
                "route": output.routing,
                "request_id": req_id,
                "steps": output.steps,
                "chart_path": output.chart_path,
                "source_file": output.source_file,
                "hitl_used": output.hitl_used,
                "pending_approvals_created": output.pending_approvals_created,
                "error": output.error,
            },
        )
