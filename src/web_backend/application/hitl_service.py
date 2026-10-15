"""HITL Feedback Application Service for Web Backend — Kế thừa BaseService."""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from common.base.base_model import CustomBaseModel
from common.base.base_service import BaseService
from common.logging.logger import get_logger

logger = get_logger("web_backend.application.hitl")

from web_backend.infra.database.connection import get_connection
from web_backend.infra.database.repositories import (
    HITLEvaluationRepository,
    MessageRepository,
    SessionRepository,
)


SIGNAL_SCORE: dict[str, tuple[float, str]] = {
    "thumbs_up": (1.0, "explicit"),
    "thumbs_down": (0.0, "explicit"),
    "copied": (1.0, "implicit"),
    "regenerated": (0.0, "implicit"),
    "abandoned": (0.0, "implicit"),
}


def score_for_signal(reason: str | None) -> tuple[float | None, str | None]:
    if not reason:
        return None, None
    return SIGNAL_SCORE.get(reason, (None, None))


def get_hitl_feedback_json_path() -> Path:
    """Xác định đường dẫn lưu trữ tệp hitl_feedback.json."""
    raw = os.environ.get("HITL_FEEDBACK_JSON_PATH")
    if raw:
        path = Path(raw)
    else:
        root = None
        p = Path(__file__).resolve().parent
        for _ in range(6):
            if (p / "pyproject.toml").is_file():
                root = p
                break
            p = p.parent
        if root is None:
            root = Path(__file__).resolve().parents[3]
        path = root / "resources" / "data" / "hitl_feedback.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


class HitlFeedbackInput(CustomBaseModel):
    eval_id: str | None = None
    message_id: str | None = None
    session_id: str | None = None
    rating: int | None = None
    is_positive: bool = True
    reason: str | None = None
    question: str | None = None
    answer: str | None = None
    feedback_text: str | None = None
    user_id: str = "default"


class HitlFeedbackOutput(CustomBaseModel):
    id: str
    message_id: str | None = None
    session_id: str | None = None
    rating: int | None = None
    is_positive: bool = True
    reason: str | None = None
    feedback_text: str | None = None
    signal_score: float | None = None
    feedback_source: str | None = None
    created_at: str


class HitlService(BaseService):
    """Application Service quản lý phản hồi đánh giá và đo lường telemetry HITL."""

    def __init__(self, conn: sqlite3.Connection | None = None) -> None:
        self._conn = conn

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is not None:
            return self._conn
        return get_connection()

    def process(self, inputs: HitlFeedbackInput) -> HitlFeedbackOutput:
        """Thực thi ghi nhận phản hồi và tính điểm theo chuẩn BaseService."""
        conn = self._get_conn()
        should_close = self._conn is None
        try:
            s_repo = SessionRepository(conn)
            m_repo = MessageRepository(conn)
            repo = HITLEvaluationRepository(conn)
            score, source = score_for_signal(inputs.reason)

            sid = (inputs.session_id or "").strip()
            if not sid or s_repo.get(sid) is None:
                session = s_repo.create(title=inputs.question or "Đánh giá HITL", session_id=sid or None)
                sid = session.id

            mid = (inputs.message_id or "").strip()
            if not mid or m_repo.get(mid) is None:
                msg = m_repo.create(
                    session_id=sid,
                    role="assistant",
                    content=inputs.answer or "",
                    message_id=mid or None,
                )
                mid = msg.id

            fb_content = inputs.feedback_text if inputs.feedback_text is not None else inputs.feedback
            record = repo.create(
                message_id=mid,
                session_id=sid,
                is_positive=inputs.is_positive,
                rating=inputs.rating,
                feedback=fb_content,
                reason=inputs.reason,
                question=inputs.question,
                answer=inputs.answer,
                signal_score=score,
                feedback_source=source,
            )

            # Xuất telemetry JSON
            self._export_telemetry(
                eval_id=record.id,
                message_id=inputs.message_id or "",
                session_id=inputs.session_id or "",
                rating=inputs.rating,
                is_positive=inputs.is_positive,
                reason=inputs.reason,
                question=inputs.question,
                answer=inputs.answer,
                user_feedback=inputs.feedback_text,
                created_at=str(getattr(record, "created_at", "")),
            )

            fb_val = getattr(record, "feedback_text", None) or getattr(record, "feedback", None)
            return HitlFeedbackOutput(
                id=record.id,
                message_id=getattr(record, "message_id", None),
                session_id=getattr(record, "session_id", None),
                rating=getattr(record, "rating", None),
                is_positive=bool(getattr(record, "is_positive", True)),
                reason=getattr(record, "reason", None),
                feedback_text=fb_val,
                signal_score=score,
                feedback_source=source,
                created_at=str(getattr(record, "created_at", "")),
            )
        finally:
            if should_close:
                conn.close()

    def _export_telemetry(
        self,
        eval_id: str,
        message_id: str,
        session_id: str,
        rating: int | None,
        is_positive: bool,
        reason: str | None,
        question: str | None = None,
        answer: str | None = None,
        user_feedback: str | None = None,
        created_at: str | None = None,
    ) -> None:
        try:
            dest = get_hitl_feedback_json_path()
            ts = created_at or datetime.now(timezone.utc).isoformat()
            tokens_used = max(10, int((len(question or "") + len(answer or "")) / 3.5)) if (question or answer) else None

            entry = {
                "id": eval_id,
                "timestamp": ts,
                "session_id": session_id,
                "message_id": message_id,
                "question": question,
                "answer": answer,
                "tokens_used": tokens_used,
                "rating": rating,
                "is_positive": is_positive,
                "reason": reason,
                "user_feedback": user_feedback,
            }

            records = []
            if dest.is_file():
                try:
                    with open(dest, "r", encoding="utf-8") as f:
                        records = json.load(f)
                    if not isinstance(records, list):
                        records = []
                except Exception:
                    records = []

            records.append(entry)
            with open(dest, "w", encoding="utf-8") as f:
                json.dump(records, f, ensure_ascii=False, indent=2)
        except Exception as exc:
            logger.warning(f"Could not export HITL telemetry to JSON: {exc}")

    def list_feedback(
        self,
        session_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Any]:
        conn = self._get_conn()
        should_close = self._conn is None
        try:
            repo = HITLEvaluationRepository(conn)
            return repo.list_all(session_id=session_id, limit=limit, offset=offset)
        finally:
            if should_close:
                conn.close()
