"""Swarm Orchestrator service — Điều phối LangGraph Multi-Agent Swarm (thay thế use-case answer_question).

Kế thừa BaseService từ common.base.base_service.
Cung cấp phương thức process() đồng bộ và phương thức stream() phục vụ SSE streaming.
"""

from __future__ import annotations

import queue
import threading
import uuid
from typing import TYPE_CHECKING, Any, Callable, Iterator
from pydantic import Field

from common.base.base_model import CustomBaseModel
from common.base.base_service import BaseService
from common.domain.ports import MemoryStore, NewsSource, PriceHistoryStore, PriceSource, WatchlistStore
from common.logging.logger import get_logger

if TYPE_CHECKING:  # chỉ cho IDE/type-check, lúc chạy application không import infra
    from ai_backend.infra.agents.state import AnswerQuestionResult

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


class SwarmOrchestrator(BaseService):
    """Service điều phối LangGraph Swarm Đa Tác Tử."""

    def __init__(
        self,
        *,
        graph_runner: Callable[..., AnswerQuestionResult] | None = None,  # production: run_chat_graph
        price_source: PriceSource | None = None,
        news_source: NewsSource | None = None,
        history_store: PriceHistoryStore | None = None,
        memory_store: MemoryStore | None = None,
        watchlist_store: WatchlistStore | None = None,
    ) -> None:
        self.graph_runner = graph_runner
        self.price_source = price_source
        self.news_source = news_source
        self.history_store = history_store
        self.memory_store = memory_store
        self.watchlist_store = watchlist_store

    def process(
        self,
        inputs: SwarmInput,
        event_callback: Callable[[str, dict[str, Any]], None] | None = None,
    ) -> SwarmOutput:
        """Xử lý điều phối Swarm hỏi-đáp đồng bộ. `event_callback` nhận event realtime từ các node graph."""
        q = inputs.question.strip()
        req_id = inputs.request_id
        logger.info(f"SwarmOrchestrator.process: q='{q[:50]}' user='{inputs.user_id}' req_id='{req_id}'")

        if self.graph_runner is None:
            raise RuntimeError("SwarmOrchestrator chưa được inject graph_runner (run_chat_graph)")

        # Chạy Hierarchical Swarm Graph (câu chào: guardrail_input → answer)
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
            if event_callback is not None:
                kwargs["event_callback"] = event_callback

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

        # Luồng tiêu chuẩn: chạy process() trong thread riêng, các node graph đẩy event
        # (node_start, token từ LLM, node_finish...) vào queue ngay khi phát sinh -> stream thật.
        inp = SwarmInput(
            question=q,
            user_id=user_id,
            request_id=req_id,
            watchlist=watchlist or [],
            holdings=holdings or [],
        )
        events: queue.Queue[tuple[str, Any]] = queue.Queue()
        cancel = threading.Event()

        def _worker() -> None:
            from ai_backend.infra.agents.chat.team import set_stream_cancel_event

            # Graph kiểm tra cờ này ở mỗi emit_agent_event -> dừng khi client ngắt kết nối.
            set_stream_cancel_event(cancel)
            try:
                result = self.process(inp, event_callback=lambda e, d: events.put((e, d)))
            except Exception as exc:
                logger.error(f"Lỗi SwarmOrchestrator.stream: {exc}", exc_info=True)
                result = SwarmOutput(question=q, answer="", routing="error", error=str(exc))
            finally:
                set_stream_cancel_event(None)
            events.put(("__done__", result))

        threading.Thread(target=_worker, daemon=True).start()

        streamed = False
        try:
            while True:
                event, data = events.get()
                if event == "__done__":
                    output: SwarmOutput = data
                    break
                streamed = streamed or event == "token"
                yield (event, data)
        finally:
            # Generator bị đóng sớm (client ngắt) -> báo graph dừng, khỏi tốn token LLM.
            cancel.set()

        # Graph không phát token nào (nhánh concept/diagram, lỗi...) -> gửi nguyên câu trả lời.
        if not streamed and output.answer:
            yield ("node_start", {"node": "answer"})
            yield ("token", {"delta": output.answer, "node": "answer"})
            yield ("node_finish", {"node": "answer"})

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
