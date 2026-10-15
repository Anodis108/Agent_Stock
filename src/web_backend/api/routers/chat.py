"""POST /chat — Web Chat router (Hỗ trợ SSE Streaming & JSON fallback)."""

from __future__ import annotations

import asyncio
import json
import queue
import threading
import time
from collections.abc import AsyncIterator, Callable
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

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
    mod = sys.modules.get("ai_backend.infra.graph.chat")
    if mod is not None:
        return getattr(mod, "answer_question", None)
    return None


def _get_stream_cancel_hooks() -> tuple[type[BaseException], Callable[[Any], None]]:
    mod = sys.modules.get("ai_backend.infra.graph.chat")
    if mod is not None:
        err_cls = getattr(mod, "StreamCancelledError", RuntimeError)
        set_fn = getattr(mod, "set_stream_cancel_event", lambda evt: None)
        return err_cls, set_fn
    return RuntimeError, lambda evt: None


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
    is_disconnected: Callable[[], bool] | None = None,
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
            is_disconnected=is_disconnected,
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


def stream_chat_generator(
    body: ChatRequest,
    deps: AppDeps,
    *,
    is_disconnected: Callable[[], bool] | None = None,
    cancel_event: threading.Event | None = None,
):
    """Phát các sự kiện Server-Sent Events (SSE)."""
    try:
        from common.transport import _use_http
        use_http = _use_http()
    except Exception:
        use_http = False

    if use_http:
        yield from _proxy_ai_chat_stream(
            body,
            is_disconnected=is_disconnected,
            cancel_event=cancel_event,
        )
        return

    session_id, question = _prepare_stream_session(body)
    t_start = time.perf_counter()
    cancel = cancel_event or threading.Event()

    event_queue: queue.Queue[tuple[str, dict[str, Any]] | None] = queue.Queue()

    def _event_cb(event: str, data: dict[str, Any]) -> None:
        event_queue.put((event, data))

    def _worker():
        StreamCancelledError, set_stream_cancel_event = _get_stream_cancel_hooks()
        set_stream_cancel_event(cancel)
        try:
            ans_fn = _get_chat_answer_fn()
            if ans_fn is None:
                event_queue.put(("error", {"error": "Chat service not configured"}))
                return

            result = ans_fn(
                question,
                price_source=deps.price_source,
                news_source=deps.news_source,
                history_store=deps.history_store,
                memory_store=deps.memory_store,
                user_id=body.user_id,
                event_callback=_event_cb,
            )
            payload = _format_stream_payload(result, t_start)

            trace_data = None
            if getattr(result, "steps", None) or getattr(result, "routing", None):
                trace_data = json.dumps(
                    {"steps": payload.get("steps", []), "route": payload.get("route", "")},
                    ensure_ascii=False,
                )
            chart_path = payload.get("chart_path")

            w_conn = get_connection()
            assistant_msg_id = None
            try:
                assistant_msg = MessageRepository(w_conn).create(
                    session_id=session_id,
                    role="assistant",
                    content=payload.get("answer", ""),
                    chart_path=chart_path if isinstance(chart_path, str) else None,
                    trace_data=trace_data,
                )
                assistant_msg_id = assistant_msg.id
            finally:
                w_conn.close()

            payload["session_id"] = session_id
            payload["message_id"] = assistant_msg_id
            payload["total_duration_s"] = round(time.perf_counter() - t_start, 3)
            event_queue.put(("final_answer", payload))
            event_queue.put(("complete", dict(payload)))
        except StreamCancelledError:
            event_queue.put(("error", {"error": "client disconnected"}))
        except Exception as exc:
            event_queue.put(("error", {"error": str(exc)}))
        finally:
            set_stream_cancel_event(None)
            event_queue.put(None)

    worker_thread = threading.Thread(target=_worker, daemon=True)
    worker_thread.start()

    try:
        while True:
            if is_disconnected and is_disconnected():
                cancel.set()
                break
            try:
                item = event_queue.get(timeout=0.2)
            except queue.Empty:
                if not worker_thread.is_alive():
                    break
                continue
            if item is None:
                break
            event, data = item
            yield f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
    finally:
        cancel.set()


async def stream_chat_generator_async(
    body: ChatRequest,
    deps: AppDeps,
    request: Request,
) -> AsyncIterator[str]:
    """Async SSE wrapper — dừng khi client ngắt kết nối."""
    cancel = threading.Event()
    loop = asyncio.get_running_loop()
    chunks: queue.Queue[str | None] = queue.Queue()

    def _run_sync_gen() -> None:
        try:
            for chunk in stream_chat_generator(
                body,
                deps,
                is_disconnected=lambda: cancel.is_set(),
                cancel_event=cancel,
            ):
                chunks.put(chunk)
        finally:
            chunks.put(None)

    loop.run_in_executor(None, _run_sync_gen)

    while True:
        if await request.is_disconnected():
            cancel.set()
            break
        try:
            chunk = await asyncio.to_thread(chunks.get, True, 0.2)
        except queue.Empty:
            continue
        if chunk is None:
            break
        yield chunk


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
            stream_chat_generator_async(body, deps, request),
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
                    hitl_used=final_data.get("hitl_used", False),
                    pending_approvals_created=final_data.get("pending_approvals_created", 0),
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
            hitl_used=getattr(result, "hitl_used", False),
            pending_approvals_created=getattr(result, "pending_approvals_created", 0),
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
    """Endpoint Server-Sent Events (SSE) phát trực tiếp tiến trình trả lời câu hỏi."""
    return StreamingResponse(
        stream_chat_generator_async(body, deps, request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
