"""POST /chat — Web Chat router (Hỗ trợ SSE Streaming & JSON fallback)."""

from __future__ import annotations

import asyncio
import json
import threading
import time
from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from starlette.concurrency import iterate_in_threadpool

from common.logging.logger import correlation_id_ctx, get_logger
from common.transport.transport import stream_remote_sse
from web_backend.api.deps import AppDeps, get_app_deps
from web_backend.api.helpers.validation import normalize_question, title_from_question
from web_backend.api.models.chat import ChatRequest, ChatResponse, ChatStep

logger = get_logger("web_backend.api.routers.chat")
router = APIRouter(tags=["chat"])

from web_backend.infra.database.connection import get_connection
from web_backend.infra.database.repositories import MessageRepository, SessionRepository

import sys

_chat_answer_fn: Any = None


def set_chat_answer_fn(fn: Any) -> None:
    """Thiết lập hàm xử lý chat thủ công (dành cho dependency injection hoặc tests)."""
    global _chat_answer_fn
    _chat_answer_fn = fn


def _get_chat_answer_fn() -> Any:
    if _chat_answer_fn is not None:
        return _chat_answer_fn
    mod = sys.modules.get("ai_backend.domain.agents.graph")
    if mod is None:
        return None

    def answer(question: str, *, user_id: str, request_id: str, **request_deps: Any) -> Any:
        import asyncio

        from ai_backend.domain.agents.graph import start_graph

        async def _run() -> Any:
            result = None
            async for kind, payload in start_graph(
                "chat", question, request_deps, user_id=user_id, request_id=request_id
            ):
                if kind == "result":
                    result = payload  # đọc hết generator: save_long_term_memory chạy sau result
            if result is None:
                raise RuntimeError("start_graph không yield result")
            return result

        return asyncio.run(_run())["final_answer"]

    return answer


def _format_stream_payload(result: Any, t_start: float) -> dict[str, Any]:
    mod = sys.modules.get("ai_backend.infra.llm.chat_stream")
    if mod is not None and hasattr(mod, "swarm_public_payload"):
        try:
            return mod.swarm_public_payload(result, started=t_start)
        except Exception:
            pass
    return {
        "answer": getattr(result, "answer", "") or "",
        "steps": [s.model_dump() if hasattr(s, "model_dump") else s for s in (getattr(result, "steps", None) or [])]
        if hasattr(getattr(result, "steps", None), "__iter__")
        else [],
        "drawed_paths": list(getattr(result, "drawed_paths", None) or []),
    }


def _prepare_stream_session(body: ChatRequest) -> tuple[str, str]:
    """Tạo/tìm session và lưu tin nhắn user — trả về (session_id, question)."""
    question = normalize_question(body.question)
    conn = get_connection()
    try:
        s_repo = SessionRepository(conn)
        m_repo = MessageRepository(conn)

        session_id = (body.session_id or "").strip()
        if session_id:
            session = s_repo.get(session_id)
            if session is None:
                session = s_repo.create(title=title_from_question(question), session_id=session_id)
            elif session.title == "Cuộc trò chuyện mới":
                s_repo.update_title(session.id, title_from_question(question))
            else:
                s_repo.touch(session.id)
        else:
            session = s_repo.create(title=title_from_question(question))
            session_id = session.id

        m_repo.create(
            session_id=session_id,
            role="user",
            content=question,
        )
    finally:
        conn.close()
    return session_id, question


def _save_stream_assistant(session_id: str, data: dict[str, Any]) -> str | None:
    """Lưu câu trả lời sau khi AI gửi final_answer hoặc complete."""
    drawed_paths = data.get("drawed_paths") or []
    conn = get_connection()
    try:
        msg = MessageRepository(conn).create(
            session_id=session_id,
            role="assistant",
            content=str(data.get("answer") or ""),
            chart_path=json.dumps(drawed_paths) if drawed_paths else None,  # cột chart_path lưu JSON list drawed_paths
        )
        return msg.id
    finally:
        conn.close()


def _proxy_ai_chat_stream(
    body: ChatRequest,
    *,
    request_id: str,
    cancel_event: threading.Event | None = None,
):
    """Ủy thác cho AI microservice stream SSE, web lưu session và tin nhắn."""
    session_id, question = _prepare_stream_session(body)
    saved = False
    message_id: str | None = None
    cancel = cancel_event or threading.Event()
    try:
        for event, data in stream_remote_sse(
            question=question,
            user_id=body.user_id,
            request_id=request_id,
            cancel_event=cancel,
        ):
            if event in ("final_answer", "complete"):
                if not saved:
                    try:
                        message_id = _save_stream_assistant(session_id, data)
                    except Exception as exc:
                        data = {
                            **data,
                            "error": data.get("error") or f"lưu hội thoại lỗi: {exc}",
                        }
                    saved = True
                data = {**data, "session_id": session_id, "message_id": message_id}
            yield f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
    finally:
        cancel.set()


async def stream_chat_generator_async(body: ChatRequest, deps: AppDeps, request_id: str) -> AsyncIterator[str]:
    """SSE token câu trả lời + `complete` (đã lưu hội thoại). Client ngắt kết nối → generator bị huỷ, graph dừng theo."""
    try:
        from common.transport import _use_http
        use_http = _use_http()
    except Exception:
        use_http = False

    if use_http:
        cancel = threading.Event()
        try:
            async for chunk in iterate_in_threadpool(_proxy_ai_chat_stream(body, request_id=request_id, cancel_event=cancel)):
                yield chunk
        finally:
            cancel.set()
        return

    def sse(event: str, data: dict[str, Any]) -> str:
        return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

    graph_mod = sys.modules.get("ai_backend.domain.agents.graph")
    if graph_mod is None:
        yield sse("error", {"error": "Chat service not configured"})
        return

    session_id, question = _prepare_stream_session(body)
    t_start = time.perf_counter()
    request_deps = {
        "price_source": deps.price_source,
        "news_source": deps.news_source,
        "history_store": deps.history_store,
        "memory_store": deps.memory_store,
    }
    try:
        done = False
        async for kind, payload in graph_mod.start_graph(
            "chat", question, request_deps, user_id=body.user_id, request_id=request_id
        ):
            if kind == "result":  # answer xong → gửi complete ngay; graph chạy tiếp save_long_term_memory
                payload = _format_stream_payload(payload, t_start)
                payload["message_id"] = _save_stream_assistant(session_id, payload)
                payload["session_id"] = session_id
                yield sse("complete", payload)
                done = True
        if not done:
            raise RuntimeError("start_graph không yield result")
    except Exception as exc:  # noqa: BLE001 — báo lỗi cho client thay vì cắt stream
        yield sse("error", {"error": str(exc)})


@router.post("/chat", response_model=ChatResponse)
@router.post("/api/v1/chat", response_model=ChatResponse)
@router.post("/api/chat", response_model=ChatResponse)
def post_chat(
    request: Request,
    body: ChatRequest,
    deps: AppDeps = Depends(get_app_deps),
) -> Any:
    request_id = correlation_id_ctx.get()  # CorrelationIdMiddleware sinh 1 lần ở biên web → truyền xuống AI
    accept_header = (request.headers.get("accept") or "").lower()
    is_stream = "text/event-stream" in accept_header or request.query_params.get("stream") == "true"
    if is_stream:
        return StreamingResponse(
            stream_chat_generator_async(body, deps, request_id),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    question = normalize_question(body.question)

    conn = get_connection()
    try:
        s_repo = SessionRepository(conn)
        m_repo = MessageRepository(conn)

        # 1. Quản lý Session
        session_id = (body.session_id or "").strip()
        if session_id:
            session = s_repo.get(session_id)
            if session is None:
                session = s_repo.create(title=title_from_question(question), session_id=session_id)
            elif session.title == "Cuộc trò chuyện mới":
                s_repo.update_title(session.id, title_from_question(question))
            else:
                s_repo.touch(session.id)
        else:
            session = s_repo.create(title=title_from_question(question))
            session_id = session.id

        # 2. Lưu tin nhắn người dùng
        m_repo.create(
            session_id=session_id,
            role="user",
            content=question,
        )

        ans_fn = _get_chat_answer_fn()
        if ans_fn is None:
            try:
                from common.transport.transport import _use_http, stream_remote_sse
                use_http = _use_http()
            except Exception:
                use_http = False

            if use_http:
                final_data: dict[str, Any] = {}
                for event, data in stream_remote_sse(
                    question=question,
                    user_id=body.user_id,
                    request_id=request_id,
                ):
                    if event in ("final_answer", "complete"):
                        final_data.update(data)

                answer_text = str(final_data.get("answer") or "")
                drawed_paths = final_data.get("drawed_paths") or []
                steps_list = final_data.get("steps") or []

                assistant_msg = m_repo.create(
                    session_id=session_id,
                    role="assistant",
                    content=answer_text,
                    chart_path=json.dumps(drawed_paths) if drawed_paths else None,
                )

                validated_steps = []
                for s in steps_list:
                    try:
                        validated_steps.append(ChatStep.model_validate(s))
                    except Exception:
                        pass

                return ChatResponse(
                    question=question,
                    answer=answer_text,
                    steps=validated_steps,
                    error=final_data.get("error"),
                    drawed_paths=drawed_paths,
                    session_id=session_id,
                    message_id=assistant_msg.id,
                )

            return ChatResponse(
                question=question,
                answer="Hệ thống chat chưa được cấu hình.",
                session_id=session_id,
            )

        result = ans_fn(
            question,
            price_source=deps.price_source,
            news_source=deps.news_source,
            history_store=deps.history_store,
            memory_store=deps.memory_store,
            user_id=body.user_id,
            request_id=request_id,
        )

        drawed_paths = list(getattr(result, "drawed_paths", None) or [])

        # 3. Lưu tin nhắn trợ lý trả lời
        assistant_msg = m_repo.create(
            session_id=session_id,
            role="assistant",
            content=result.answer or "",
            chart_path=json.dumps(drawed_paths) if drawed_paths else None,
        )

        return ChatResponse(
            question=result.question,
            answer=result.answer,
            error=getattr(result, "error", None),
            drawed_paths=drawed_paths,
            session_id=session_id,
            message_id=assistant_msg.id,
        )
    finally:
        conn.close()


@router.post("/chat/stream")
@router.post("/api/v1/chat/stream")
@router.post("/api/chat/stream")
async def post_chat_stream(
    request: Request,
    body: ChatRequest,
    deps: AppDeps = Depends(get_app_deps),
) -> StreamingResponse:
    """Endpoint Server-Sent Events (SSE) phát token câu trả lời."""
    return StreamingResponse(
        stream_chat_generator_async(body, deps, correlation_id_ctx.get()),  # đọc trước khi stream (contextvar reset sau dispatch)
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
