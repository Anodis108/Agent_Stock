"""Chat Gateway Service for Web Backend — Điều phối hội thoại & giao tiếp với AI microservice."""

from __future__ import annotations

import asyncio
import json
import queue
import threading
import time
from collections.abc import AsyncIterator, Callable
from typing import Any

from common.base.base_model import CustomBaseModel
from common.base.base_service import AsyncBaseService
from common.logging.logger import get_logger
from common.transport.transport import stream_remote_sse
from web_backend.api.helpers.validation import normalize_question, title_from_question
from web_backend.api.models.chat import ChatRequest, ChatResponse, ChatStep

logger = get_logger("web_backend.application.chat_gateway")

from web_backend.infra.database.connection import get_connection
from web_backend.infra.database.repositories import MessageRepository, SessionRepository



class ChatGatewayInput(CustomBaseModel):
    question: str
    user_id: str = "default"
    session_id: str | None = None


class ChatGatewayOutput(CustomBaseModel):
    question: str
    answer: str
    session_id: str
    message_id: str | None = None
    steps: list[Any] = []
    route: str = ""
    error: str | None = None


class ChatGatewayService(AsyncBaseService):
    """Async Application Service điều phối luồng hỏi-đáp, quản lý session và chuyển tiếp SSE."""

    def __init__(self, answer_fn: Callable[..., Any] | None = None) -> None:
        self.answer_fn = answer_fn

    def _prepare_session(self, question: str, session_id: str | None) -> tuple[str, str]:
        q = normalize_question(question)
        conn = get_connection()
        try:
            s_repo = SessionRepository(conn)
            m_repo = MessageRepository(conn)

            sid = (session_id or "").strip()
            if sid:
                session = s_repo.get(sid)
                if session is None:
                    session = s_repo.create(title=title_from_question(q), session_id=sid)
                elif session.title == "Cuộc trò chuyện mới":
                    s_repo.update_title(session.id, title_from_question(q))
                else:
                    s_repo.touch(session.id)
            else:
                session = s_repo.create(title=title_from_question(q))
                sid = session.id

            m_repo.create(
                session_id=sid,
                role="user",
                content=q,
            )
            return sid, q
        finally:
            conn.close()

    def _save_assistant_message(
        self, session_id: str, content: str, chart_path: str | None = None, trace_data: str | None = None
    ) -> str:
        conn = get_connection()
        try:
            m_repo = MessageRepository(conn)
            msg = m_repo.create(
                session_id=session_id,
                role="assistant",
                content=content,
                chart_path=chart_path,
                trace_data=trace_data,
            )
            return msg.id
        finally:
            conn.close()

    async def process(self, inputs: ChatGatewayInput) -> ChatGatewayOutput:
        """Thực hiện xử lý câu hỏi synchronous/fallback và lưu hội thoại."""
        sid, q = self._prepare_session(inputs.question, inputs.session_id)

        if self.answer_fn is not None:
            result = self.answer_fn(q, user_id=inputs.user_id)
            answer_text = getattr(result, "answer", str(result))
            steps = getattr(result, "steps", [])
            route = str(getattr(getattr(result, "routing", None), "route", ""))
        else:
            answer_text = f"Phản hồi cho câu hỏi: '{q}'."
            steps = []
            route = "DIRECT"

        msg_id = self._save_assistant_message(sid, answer_text)
        return ChatGatewayOutput(
            question=q,
            answer=answer_text,
            session_id=sid,
            message_id=msg_id,
            steps=steps,
            route=route,
        )

    async def stream_chat(
        self,
        inputs: ChatGatewayInput,
        cancel_event: threading.Event | None = None,
        is_disconnected: Callable[[], bool] | None = None,
    ) -> AsyncIterator[str]:
        """Stream SSE từ AI microservice hoặc fallback generator."""
        sid, q = self._prepare_session(inputs.question, inputs.session_id)
        cancel = cancel_event or threading.Event()
        saved = False
        message_id: str | None = None

        try:
            for event, data in stream_remote_sse(
                question=q,
                user_id=inputs.user_id,
                cancel_event=cancel,
                is_disconnected=is_disconnected,
            ):
                if event in ("final_answer", "complete") and not saved:
                    answer_text = str(data.get("answer") or "")
                    chart_path = data.get("chart_path")
                    trace_data = json.dumps(
                        {"steps": data.get("steps") or [], "route": data.get("route") or ""},
                        ensure_ascii=False,
                    )
                    message_id = self._save_assistant_message(sid, answer_text, chart_path, trace_data)
                    saved = True

                data = {**data, "session_id": sid, "message_id": message_id}
                yield f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
        finally:
            cancel.set()
