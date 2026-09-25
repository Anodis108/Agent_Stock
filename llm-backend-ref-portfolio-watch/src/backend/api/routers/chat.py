"""POST /chat — hỏi-đáp (không qua HITL)."""

from __future__ import annotations

import json
import queue
import threading
import time
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend.api.deps import AppDeps, get_app_deps
from backend.api.helpers.validation import normalize_question, title_from_question
from backend.application.answer_question import answer_question
from backend.database.connection import get_connection
from backend.database.repositories import MessageRepository, SessionRepository

router = APIRouter(tags=["chat"])


class ChatRequest(BaseModel):
    question: str = Field(description="Câu hỏi tự do")
    user_id: str = "default"
    session_id: str | None = None


class ChatStep(BaseModel):
    id: str
    name: str
    status: str = "done"
    detail: str | None = None


class ChatResponse(BaseModel):
    question: str
    rewritten: str
    symbol: str | None = None
    intent: str = ""
    agents_to_call: list[str] = Field(default_factory=list)
    route: str = ""
    reason: str = ""
    answer: str
    steps: list[ChatStep] = Field(default_factory=list)
    hitl_used: bool = False
    pending_approvals_created: int = 0
    error: str | None = None
    price: dict[str, Any] | None = None
    news_count: int = 0
    news: list[dict[str, Any]] = Field(default_factory=list)
    news_error: str | None = None
    severity: dict[str, Any] | None = None
    chart_path: str | None = None
    session_id: str | None = None
    message_id: str | None = None


@router.post("/chat", response_model=ChatResponse)
@router.post("/api/v1/chat", response_model=ChatResponse)
@router.post("/api/chat", response_model=ChatResponse)
def post_chat(
    body: ChatRequest,
    deps: AppDeps = Depends(get_app_deps),
) -> ChatResponse:
    question = normalize_question(body.question)

    conn = get_connection()
    try:
        s_repo = SessionRepository(conn)
        m_repo = MessageRepository(conn)

        # 1. Quản lý Session: tìm session cũ hoặc tạo session mới
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

        # 2. Lưu tin nhắn người dùng vào SQLite
        m_repo.create(
            session_id=session_id,
            role="user",
            content=question,
        )

        result = answer_question(
            question,
            price_source=deps.price_source,
            news_source=deps.news_source,
            history_store=deps.history_store,
            memory_store=deps.memory_store,
            user_id=body.user_id,
        )

        price_payload: dict[str, Any] | None = None
        if result.price is not None:
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
        if result.news is not None:
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
        if result.eval_result is not None:
            severity = result.eval_result.severity.model_dump(mode="json")

        chart_path = getattr(result, "chart_path", None)
        trace_data = None
        if result.steps or getattr(result, "routing", None):
            trace_dict = {
                "steps": [s.model_dump() if hasattr(s, "model_dump") else s for s in (result.steps or [])] if hasattr(result.steps, "__iter__") else [],
                "route": str(getattr(result.routing.route, "value", result.routing.route)) if getattr(result, "routing", None) else "",
            }
            trace_data = json.dumps(trace_dict, ensure_ascii=False)

        # 3. Lưu tin nhắn trợ lý trả lời vào SQLite
        assistant_msg = m_repo.create(
            session_id=session_id,
            role="assistant",
            content=result.answer or "",
            chart_path=chart_path,
            trace_data=trace_data,
        )

        return ChatResponse(
            question=result.question,
            rewritten=result.rewritten.rewritten,
            symbol=result.rewritten.symbol,
            intent=result.rewritten.intent,
            agents_to_call=list(result.routing.agents_to_call or []),
            route=str(getattr(result.routing.route, "value", result.routing.route)),
            reason=result.routing.reason or "",
            answer=result.answer,
            steps=[ChatStep.model_validate(s) for s in (result.steps or [])],
            hitl_used=result.hitl_used,
            pending_approvals_created=result.pending_approvals_created,
            error=result.error,
            price=price_payload,
            news_count=len(news_items),
            news=news_items,
            news_error=news_error,
            severity=severity,
            chart_path=chart_path,
            session_id=session_id,
            message_id=assistant_msg.id,
        )
    finally:
        conn.close()


def stream_chat_generator(
    body: ChatRequest,
    deps: AppDeps,
):
    """Generator phát các sự kiện Server-Sent Events (SSE) theo thời gian thực:
    - node_start: Khi một agent/node bắt đầu chạy
    - node_finish: Khi một agent/node hoàn thành, kèm thời gian thực thi (duration_s, duration_ms)
    - token: Từng mẩu từ/token phản hồi trực tiếp từ LLM
    - complete: Trả lời hoàn chỉnh và toàn bộ metadata
    - error: Khi gặp sự cố ngoài ý muốn
    """
    question = normalize_question(body.question)
    t_start = time.perf_counter()

    conn = get_connection()
    try:
        s_repo = SessionRepository(conn)
        m_repo = MessageRepository(conn)

        # 1. Quản lý Session: tìm session cũ hoặc tạo session mới
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

        # 2. Lưu tin nhắn người dùng vào SQLite
        m_repo.create(
            session_id=session_id,
            role="user",
            content=question,
        )
    finally:
        conn.close()

    event_queue: queue.Queue[tuple[str, dict[str, Any]] | None] = queue.Queue()

    def _event_cb(event: str, data: dict[str, Any]) -> None:
        event_queue.put((event, data))

    def _worker():
        try:
            result = answer_question(
                question,
                price_source=deps.price_source,
                news_source=deps.news_source,
                history_store=deps.history_store,
                memory_store=deps.memory_store,
                user_id=body.user_id,
                event_callback=_event_cb,
            )

            price_payload: dict[str, Any] | None = None
            if result.price is not None:
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
            if result.news is not None:
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
            if result.eval_result is not None:
                severity = result.eval_result.severity.model_dump(mode="json")

            chart_path = getattr(result, "chart_path", None)
            raw_steps = [s.model_dump() if hasattr(s, "model_dump") else s for s in (result.steps or [])]
            trace_data = None
            if result.steps or getattr(result, "routing", None):
                trace_dict = {
                    "steps": raw_steps,
                    "route": str(getattr(result.routing.route, "value", result.routing.route)) if getattr(result, "routing", None) else "",
                }
                trace_data = json.dumps(trace_dict, ensure_ascii=False)

            # Lưu tin nhắn trợ lý vào SQLite trong worker thread
            w_conn = get_connection()
            assistant_msg_id = None
            try:
                w_m_repo = MessageRepository(w_conn)
                assistant_msg = w_m_repo.create(
                    session_id=session_id,
                    role="assistant",
                    content=result.answer or "",
                    chart_path=chart_path,
                    trace_data=trace_data,
                )
                assistant_msg_id = assistant_msg.id
            finally:
                w_conn.close()

            total_duration_s = round(time.perf_counter() - t_start, 3)
            complete_data = {
                "question": result.question,
                "rewritten": result.rewritten.rewritten if hasattr(result, "rewritten") and result.rewritten else "",
                "symbol": result.rewritten.symbol if hasattr(result, "rewritten") and result.rewritten else None,
                "intent": result.rewritten.intent if hasattr(result, "rewritten") and result.rewritten else "",
                "agents_to_call": list(result.routing.agents_to_call or []) if getattr(result, "routing", None) else [],
                "route": str(getattr(result.routing.route, "value", result.routing.route)) if getattr(result, "routing", None) else "",
                "reason": result.routing.reason or "" if getattr(result, "routing", None) else "",
                "answer": result.answer or "",
                "steps": raw_steps,
                "hitl_used": result.hitl_used,
                "pending_approvals_created": result.pending_approvals_created,
                "error": result.error,
                "price": price_payload,
                "news_count": len(news_items),
                "news": news_items,
                "news_error": news_error,
                "severity": severity,
                "chart_path": chart_path,
                "session_id": session_id,
                "message_id": assistant_msg_id,
                "total_duration_s": total_duration_s,
            }
            event_queue.put(("complete", complete_data))
        except Exception as exc:
            event_queue.put(("error", {"error": str(exc)}))
        finally:
            event_queue.put(None)

    worker_thread = threading.Thread(target=_worker, daemon=True)
    worker_thread.start()

    while True:
        item = event_queue.get()
        if item is None:
            break
        event, data = item
        yield f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/chat/stream")
@router.post("/api/v1/chat/stream")
@router.post("/api/chat/stream")
def post_chat_stream(
    body: ChatRequest,
    deps: AppDeps = Depends(get_app_deps),
) -> StreamingResponse:
    """Endpoint Server-Sent Events (SSE) phát trực tiếp tiến trình chạy của từng agent và stream từng token của câu trả lời."""
    return StreamingResponse(
        stream_chat_generator(body, deps),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


