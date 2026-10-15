"""SSE Streaming router for AI Swarm Graph (/v1/chat/stream)."""

from __future__ import annotations

import json
import threading
from typing import Any, Iterator

from fastapi import APIRouter, Depends, Header
from fastapi.responses import StreamingResponse

from ai_backend.api.deps import AiDeps, get_ai_deps
from ai_backend.api.models.stream_models import (
    ChatStreamRequest,
    CompleteEvent,
    NodeFinish,
    NodeStart,
    TokenEvent,
)
from common.logging.logger import get_correlation_id, get_logger

logger = get_logger("ai_backend.api.chat_stream")

router = APIRouter(prefix="/v1", tags=["ai-stream"])
alias_router = APIRouter(tags=["ai-stream-alias"])


def _format_sse(event: str, data: dict[str, Any]) -> str:
    """Định dạng bản tin theo tiêu chuẩn Server-Sent Events (SSE)."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _generate_fallback_stream(
    question: str,
    request_id: str | None = None,
    user_id: str = "default",
) -> Iterator[str]:
    """Phát luồng SSE mô phỏng chuẩn khi chưa có Swarm Orchestrator (hỗ trợ kiểm thử cô lập)."""
    # 1. Node Start: Supervisor
    yield _format_sse(
        "node_start",
        NodeStart(node="supervisor", input_data={"question": question, "user_id": user_id}).model_dump(mode="json"),
    )

    # 2. Node Finish: Supervisor
    yield _format_sse(
        "node_finish",
        NodeFinish(node="supervisor", output_data={"route": "market", "agents": ["price_agent"]}).model_dump(mode="json"),
    )

    # 3. Node Start: Answer Composer
    yield _format_sse(
        "node_start",
        NodeStart(node="answer_composer", input_data={"question": question}).model_dump(mode="json"),
    )

    # 4. Token Events
    tokens = [
        "Xin", " chào! ", "Tôi ", "là ", "trợ ", "lý ", "AI ", "phân ", "tích ",
        "chứng ", "khoán ", "Vnstock ", "Swarm. ", "Câu ", "hỏi: ", f"'{question}'.",
    ]
    for idx, tok in enumerate(tokens):
        yield _format_sse(
            "token",
            TokenEvent(token=tok, node="answer_composer", index=idx).model_dump(mode="json"),
        )

    # 5. Node Finish: Answer Composer
    yield _format_sse(
        "node_finish",
        NodeFinish(node="answer_composer", duration_ms=45).model_dump(mode="json"),
    )

    # 6. Complete Event
    full_answer = "".join(tokens)
    complete_payload = CompleteEvent(
        answer=full_answer,
        route="market",
        request_id=request_id,
        steps=[
            {"id": "step_1", "name": "supervisor", "status": "done"},
            {"id": "step_2", "name": "answer_composer", "status": "done"},
        ],
    ).model_dump(mode="json")
    yield _format_sse("complete", complete_payload)


@router.post("/chat/stream", summary="SSE Streaming token và tiến trình Agent Swarm")
@alias_router.post("/chat/stream", summary="SSE Streaming token alias")
def stream_chat(
    body: ChatStreamRequest,
    deps: AiDeps = Depends(get_ai_deps),
    x_request_id: str | None = Header(default=None, alias="X-Request-Id"),
) -> StreamingResponse:
    """Tiếp nhận câu hỏi, điều phối LangGraph Swarm và truyền dữ liệu SSE về Web Backend."""
    question = body.question.strip()
    request_id = (body.request_id or x_request_id or get_correlation_id() or "").strip() or None
    logger.info(f"Bắt đầu stream SSE cho câu hỏi '{question[:50]}' [req_id={request_id}]")

    def _event_generator() -> Iterator[str]:
        # Nếu có SwarmOrchestrator được inject từ tầng Application (Phase 3.2)
        if deps.swarm_orchestrator is not None and hasattr(deps.swarm_orchestrator, "stream"):
            try:
                for event, data in deps.swarm_orchestrator.stream(
                    question=question,
                    user_id=body.user_id,
                    request_id=request_id,
                    watchlist=body.watchlist,
                    holdings=body.holdings,
                ):
                    yield _format_sse(event, data)
                return
            except Exception as exc:
                logger.error(f"Lỗi Swarm Orchestrator stream: {exc}", exc_info=True)
                yield _format_sse("error", {"error": str(exc), "request_id": request_id})
                return

        # Luồng stream tiêu chuẩn độc lập đảm bảo phản hồi tức thì và kiểm thử offline
        for chunk in _generate_fallback_stream(question, request_id=request_id, user_id=body.user_id):
            yield chunk

    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
