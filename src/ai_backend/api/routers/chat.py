"""Chat router cho AI Swarm Graph (/v1/chat, /v1/chat/stream-sse)."""

from __future__ import annotations

import json
from typing import Any, AsyncIterator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from starlette.concurrency import iterate_in_threadpool

from ai_backend.api.models.stream_models import ChatStreamRequest
from ai_backend.application.swarm_orchestrator import SwarmInput, SwarmOrchestrator, SwarmOutput
from common.logging.logger import get_logger

logger = get_logger("ai_backend.api.chat")

router = APIRouter(prefix="/v1", tags=["ai-stream"])

def _format_sse(event: str, data: dict[str, Any]) -> str:
    """Định dạng bản tin theo tiêu chuẩn Server-Sent Events (SSE)."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/chat", response_model=SwarmOutput, summary="Hỏi-đáp Agent Swarm (non-streaming)")
def chat(body: ChatStreamRequest, request: Request) -> SwarmOutput:
    """Chạy toàn bộ Swarm rồi trả về câu trả lời hoàn chỉnh trong một response JSON."""
    
    request_id = body.request_id
    orchestrator: SwarmOrchestrator = request.app.state.orchestrator
    return orchestrator.process(
        SwarmInput(
            question=body.question.strip(),
            user_id=body.user_id,
            request_id=request_id,
            watchlist=[w.symbol for w in body.watchlist or []],
            holdings=[h.model_dump() for h in body.holdings or []],
        )
    )


@router.post("/chat/stream-sse",summary="SSE Streaming token và tiến trình Agent Swarm")
async def stream_chat(
    body: ChatStreamRequest,
    request: Request,
) -> StreamingResponse:
    """Tiếp nhận câu hỏi, điều phối LangGraph Swarm và truyền dữ liệu SSE về Web Backend."""
    question = body.question.strip()
    request_id = body.request_id

    async def _event_generator() -> AsyncIterator[str]:
        # orchestrator.stream() là generator đồng bộ (LangGraph + LLM sync) -> chạy từng bước
        # trong threadpool để không block event loop.
        
        orchestrator: SwarmOrchestrator = request.app.state.orchestrator
        events = orchestrator.stream(
            question=question,
            user_id=body.user_id,
            request_id=request_id,
            watchlist=[w.symbol for w in body.watchlist or []],
            holdings=[h.model_dump() for h in body.holdings or []],
        )
        print("event form client: ", events)
        try:
            async for event, data in iterate_in_threadpool(events):
                # Client đóng kết nối -> dừng swarm, không tốn thêm token.
                if await request.is_disconnected():
                    logger.info(f"Client ngắt kết nối, dừng stream [req_id={request_id}]")
                    break
                yield _format_sse(event, data)
        finally:
            events.close()

    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
