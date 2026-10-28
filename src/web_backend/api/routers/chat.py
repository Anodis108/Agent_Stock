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

from common.logging.logger import get_logger
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

    def answer(question: str, *, user_id: str = "default", **request_deps: Any) -> Any:
        import asyncio

        from ai_backend.domain.agents.graph import start_graph

        async def _run() -> Any:
            async for kind, payload in start_graph("chat", question, request_deps, user_id=user_id):
                if kind == "result":
                    return payload
            raise RuntimeError("start_graph không yield result")

        return asyncio.run(_run())

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
        "route": str(getattr(getattr(result, "routing", None), "route", "") or ""),
        "chart_path": getattr(result, "chart_path", None),
        "source_file": getattr(result, "source_file", None),
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
    chart_path = data.get("chart_path")
    trace_data = None
    if data.get("steps") or data.get("route"):
        trace_data = json.dumps(
            {
                "steps": data.get("steps") or [],
                "route": data.get("route") or "",
            },
            ensure_ascii=False,
        )
    conn = get_connection()
    try:
        msg = MessageRepository(conn).create(
            session_id=session_id,
            role="assistant",
            content=str(data.get("answer") or ""),
            chart_path=chart_path if isinstance(chart_path, str) else None,
            trace_data=trace_data,
        )
        return msg.id
    finally:
        conn.close()


def _proxy_ai_chat_stream(
    body: ChatRequest,
    *,
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
            user_id=body.user_id or "default",
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


async def stream_chat_generator_async(body: ChatRequest, deps: AppDeps) -> AsyncIterator[str]:
    """SSE token câu trả lời + `complete` (đã lưu hội thoại). Client ngắt kết nối → generator bị huỷ, graph dừng theo."""
    try:
        from common.transport import _use_http
        use_http = _use_http()
    except Exception:
        use_http = False

    if use_http:
        cancel = threading.Event()
        try:
            async for chunk in iterate_in_threadpool(_proxy_ai_chat_stream(body, cancel_event=cancel)):
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
        result = None
        async for kind, payload in graph_mod.start_graph(
            "chat", question, request_deps, user_id=body.user_id or "default"
        ):
            if kind == "result":
                result = payload
        if result is None:
            raise RuntimeError("start_graph không yield result")
        payload = _format_stream_payload(result, t_start)
        payload["message_id"] = _save_stream_assistant(session_id, payload)
        payload["session_id"] = session_id
        yield sse("complete", payload)
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
    accept_header = (request.headers.get("accept") or "").lower()
    is_stream = "text/event-stream" in accept_header or request.query_params.get("stream") == "true"
    if is_stream:
        return StreamingResponse(
            stream_chat_generator_async(body, deps),
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
                    user_id=body.user_id or "default",
                ):
                    if event in ("final_answer", "complete"):
                        final_data.update(data)

                answer_text = str(final_data.get("answer") or "")
                chart_path = final_data.get("chart_path")
                steps_list = final_data.get("steps") or []
                route_str = str(final_data.get("route") or "")
                trace_data = None
                if steps_list or route_str:
                    trace_data = json.dumps({"steps": steps_list, "route": route_str}, ensure_ascii=False)

                assistant_msg = m_repo.create(
                    session_id=session_id,
                    role="assistant",
                    content=answer_text,
                    chart_path=chart_path if isinstance(chart_path, str) else None,
                    trace_data=trace_data,
                )

                validated_steps = []
                for s in steps_list:
                    try:
                        validated_steps.append(ChatStep.model_validate(s))
                    except Exception:
                        pass

                return ChatResponse(
                    question=question,
                    rewritten=final_data.get("rewritten", question),
                    symbol=final_data.get("symbol"),
                    intent=final_data.get("intent", ""),
                    agents_to_call=final_data.get("agents_to_call", []),
                    route=route_str,
                    reason=final_data.get("reason", ""),
                    answer=answer_text,
                    steps=validated_steps,
                    error=final_data.get("error"),
                    price=final_data.get("price"),
                    news_count=len(final_data.get("news") or []),
                    news=final_data.get("news") or [],
                    news_error=final_data.get("news_error"),
                    severity=final_data.get("severity"),
                    chart_path=chart_path,
                    session_id=session_id,
                    message_id=assistant_msg.id,
                    source_file=final_data.get("source_file"),
                )

            return ChatResponse(
                question=question,
                rewritten=question,
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
        )

        price_payload: dict[str, Any] | None = None
        if getattr(result, "price", None) is not None:
            p = result.price
            price_payload = {
                "symbol": p.symbol,
                "latest_close": p.latest_close,
                "prev_close": p.prev_close,
                "change_pct": p.change_pct,
                "error": p.error,
            }

        news_items: list[dict[str, Any]] = []
        news_error: str | None = None
        if getattr(result, "news", None) is not None:
            news_error = result.news.error
            news_items = [
                {
                    "title": i.title,
                    "url": i.url,
                    "published_at": i.published_at,
                    "snippet": i.snippet,
                }
                for i in (result.news.items or [])
            ]

        severity = None
        if getattr(result, "eval_result", None) is not None:
            severity = result.eval_result.severity.model_dump(mode="json")

        chart_path = getattr(result, "chart_path", None)
        trace_data = None
        if getattr(result, "steps", None) or getattr(result, "routing", None):
            trace_dict = {
                "steps": [s.model_dump() if hasattr(s, "model_dump") else s for s in (result.steps or [])] if hasattr(result.steps, "__iter__") else [],
                "route": str(getattr(result.routing.route, "value", result.routing.route)) if getattr(result, "routing", None) else "",
            }
            trace_data = json.dumps(trace_dict, ensure_ascii=False)

        # 3. Lưu tin nhắn trợ lý trả lời
        assistant_msg = m_repo.create(
            session_id=session_id,
            role="assistant",
            content=result.answer or "",
            chart_path=chart_path,
            trace_data=trace_data,
        )

        return ChatResponse(
            question=result.question,
            rewritten=getattr(result.rewritten, "rewritten", ""),
            symbol=getattr(result.rewritten, "symbol", None),
            intent=getattr(result.rewritten, "intent", ""),
            agents_to_call=list(getattr(result.routing, "agents_to_call", []) or []),
            route=str(getattr(result.routing.route, "value", getattr(result.routing, "route", ""))) if getattr(result, "routing", None) else "",
            reason=getattr(result.routing, "reason", "") or "",
            answer=result.answer,
            steps=[ChatStep.model_validate(s) for s in (result.steps or [])],
            error=getattr(result, "error", None),
            price=price_payload,
            news_count=len(news_items),
            news=news_items,
            news_error=news_error,
            severity=severity,
            chart_path=chart_path,
            session_id=session_id,
            message_id=assistant_msg.id,
            source_file=getattr(result, "source_file", None),
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
        stream_chat_generator_async(body, deps),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
