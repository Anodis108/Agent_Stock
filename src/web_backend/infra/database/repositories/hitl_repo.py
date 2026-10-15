"""Repository for HITL evaluations in Web Backend."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class HITLEvaluationRecord:
    id: str
    message_id: str
    session_id: str
    rating: int | None
    feedback: str | None
    is_positive: bool
    created_at: str
    reason: str | None = None
    question: str | None = None
    answer: str | None = None
    signal_score: float | None = None
    feedback_source: str | None = None


def _hitl_from_row(row: Any) -> HITLEvaluationRecord:
    keys = row.keys() if hasattr(row, "keys") else []
    return HITLEvaluationRecord(
        id=row["id"],
        message_id=row["message_id"],
        session_id=row["session_id"],
        rating=row["rating"],
        feedback=row["feedback"],
        is_positive=bool(row["is_positive"]),
        reason=row["reason"] if "reason" in keys else None,
        question=row["question"] if "question" in keys else None,
        answer=row["answer"] if "answer" in keys else None,
        signal_score=row["signal_score"] if "signal_score" in keys else None,
        feedback_source=row["feedback_source"] if "feedback_source" in keys else None,
        created_at=row["created_at"],
    )


class HITLEvaluationRepository:
    def __init__(self, conn: Any) -> None:
        self.conn = conn

    def create(
        self,
        message_id: str,
        session_id: str,
        is_positive: bool,
        rating: int | None = None,
        feedback: str | None = None,
        reason: str | None = None,
        question: str | None = None,
        answer: str | None = None,
        signal_score: float | None = None,
        feedback_source: str | None = None,
        eval_id: str | None = None,
    ) -> HITLEvaluationRecord:
        eid = eval_id or str(uuid4())
        now = _now_iso()
        pos_int = 1 if is_positive else 0
        self.conn.execute(
            """
            INSERT INTO hitl_evaluations (
                id, message_id, session_id, rating, feedback, is_positive,
                reason, question, answer, signal_score, feedback_source, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                eid, message_id, session_id, rating, feedback, pos_int,
                reason, question, answer, signal_score, feedback_source, now,
            ),
        )
        self.conn.commit()
        return HITLEvaluationRecord(
            id=eid,
            message_id=message_id,
            session_id=session_id,
            rating=rating,
            feedback=feedback,
            is_positive=is_positive,
            created_at=now,
            reason=reason,
            question=question,
            answer=answer,
            signal_score=signal_score,
            feedback_source=feedback_source,
        )

    def get(self, eval_id: str) -> HITLEvaluationRecord | None:
        cursor = self.conn.execute(
            """
            SELECT id, message_id, session_id, rating, feedback, is_positive, reason, question, answer, signal_score, feedback_source, created_at
            FROM hitl_evaluations
            WHERE id = ?
            """,
            (eval_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return _hitl_from_row(row)

    def list_by_session(self, session_id: str) -> list[HITLEvaluationRecord]:
        cursor = self.conn.execute(
            """
            SELECT id, message_id, session_id, rating, feedback, is_positive, reason, question, answer, signal_score, feedback_source, created_at
            FROM hitl_evaluations
            WHERE session_id = ?
            ORDER BY created_at DESC
            """,
            (session_id,),
        )
        return [_hitl_from_row(row) for row in cursor.fetchall()]

    def list_all(
        self,
        limit: int = 100,
        offset: int = 0,
        session_id: str | None = None,
    ) -> list[HITLEvaluationRecord]:
        if session_id:
            cursor = self.conn.execute(
                """
                SELECT id, message_id, session_id, rating, feedback, is_positive, reason, question, answer, signal_score, feedback_source, created_at
                FROM hitl_evaluations
                WHERE session_id = ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                (session_id, limit, offset),
            )
        else:
            cursor = self.conn.execute(
                """
                SELECT id, message_id, session_id, rating, feedback, is_positive, reason, question, answer, signal_score, feedback_source, created_at
                FROM hitl_evaluations
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            )
        return [_hitl_from_row(row) for row in cursor.fetchall()]


# Short alias
HITLEvalRepo = HITLEvaluationRepository
