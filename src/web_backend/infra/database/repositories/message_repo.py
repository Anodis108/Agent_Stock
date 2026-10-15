"""Repository for Message management in Web Backend."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class MessageRecord:
    id: str
    session_id: str
    role: str  # "user" | "assistant" | "system"
    content: str
    chart_path: str | None
    trace_data: str | None
    created_at: str


class MessageRepository:
    def __init__(self, conn: Any) -> None:
        self.conn = conn

    def create(
        self,
        session_id: str,
        role: str,
        content: str,
        chart_path: str | None = None,
        trace_data: str | None = None,
        message_id: str | None = None,
    ) -> MessageRecord:
        mid = message_id or str(uuid4())
        now = _now_iso()
        self.conn.execute(
            """
            INSERT INTO messages (id, session_id, role, content, chart_path, trace_data, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (mid, session_id, role, content, chart_path, trace_data, now),
        )
        self.conn.execute(
            "UPDATE sessions SET updated_at = ? WHERE id = ?",
            (now, session_id),
        )
        self.conn.commit()
        return MessageRecord(
            id=mid,
            session_id=session_id,
            role=role,
            content=content,
            chart_path=chart_path,
            trace_data=trace_data,
            created_at=now,
        )

    def list_by_session(self, session_id: str) -> list[MessageRecord]:
        cursor = self.conn.execute(
            """
            SELECT id, session_id, role, content, chart_path, trace_data, created_at
            FROM messages
            WHERE session_id = ?
            ORDER BY created_at ASC
            """,
            (session_id,),
        )
        return [
            MessageRecord(
                id=row["id"],
                session_id=row["session_id"],
                role=row["role"],
                content=row["content"],
                chart_path=row["chart_path"],
                trace_data=row["trace_data"],
                created_at=row["created_at"],
            )
            for row in cursor.fetchall()
        ]

    def get(self, message_id: str) -> MessageRecord | None:
        cursor = self.conn.execute(
            """
            SELECT id, session_id, role, content, chart_path, trace_data, created_at
            FROM messages
            WHERE id = ?
            """,
            (message_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return MessageRecord(
            id=row["id"],
            session_id=row["session_id"],
            role=row["role"],
            content=row["content"],
            chart_path=row["chart_path"],
            trace_data=row["trace_data"],
            created_at=row["created_at"],
        )


# Short alias
MessageRepo = MessageRepository
