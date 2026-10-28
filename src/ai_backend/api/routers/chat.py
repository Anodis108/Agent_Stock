"""Chat router cho AI Swarm Graph (/v1/chat, /v1/chat/stream-sse)."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from ai_backend.api.models.stream_models import ChatResponse, ChatStreamRequest
from ai_backend.application.swarm_orchestrator import SwarmInput, SwarmOrchestrator
from ai_backend.infra.llm.chat_stream import swarm_sse

router = APIRouter(prefix="/v1", tags=["ai-stream"])


@router.post("/chat", response_model=ChatResponse, summary="Hỏi-đáp Agent Swarm (non-streaming)")
def chat(body: ChatStreamRequest, request: Request) -> ChatResponse:
    """Chạy toàn bộ Swarm rồi trả về câu trả lời hoàn chỉnh trong một response JSON."""
    orchestrator: SwarmOrchestrator = request.app.state.orchestrator
    inp = SwarmInput(
        question=body.question.strip(),
        user_id=body.user_id,
        request_id=body.request_id,
    )
    output = orchestrator.process(inp)
    return ChatResponse(
        question=output.question,
        answer=output.answer,
        rewritten_symbol=output.rewritten_symbol,
        routing=output.routing,
        steps=output.steps,
        chart_path=output.chart_path,
        error=output.error,
    )


@router.post("/chat/stream-sse", summary="SSE token câu trả lời Agent Swarm")
def stream_chat(body: ChatStreamRequest, request: Request) -> StreamingResponse:
    """Tiếp nhận câu hỏi, chạy LangGraph Swarm và stream token SSE về Web Backend."""
    orchestrator: SwarmOrchestrator = request.app.state.orchestrator
    return StreamingResponse(
        swarm_sse(body.question.strip(), orchestrator.request_deps(), user_id=body.user_id, request_id=body.request_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )
