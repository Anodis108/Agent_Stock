"""Repository for Session management in Web Backend."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class SessionRecord:
    id: str
    title: str
    created_at: str
    updated_at: str


class SessionRepository:
    def __init__(self, conn: Any) -> None:
        self.conn = conn

    def create(self, title: str = "Cuộc trò chuyện mới", session_id: str | None = None) -> SessionRecord:
        sid = session_id or str(uuid4())
        now = _now_iso()
        self.conn.execute(
            "INSERT INTO sessions (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (sid, title, now, now),
        )
        self.conn.commit()
        return SessionRecord(id=sid, title=title, created_at=now, updated_at=now)

    def get(self, session_id: str) -> SessionRecord | None:
        cursor = self.conn.execute(
            "SELECT id, title, created_at, updated_at FROM sessions WHERE id = ?",
            (session_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return SessionRecord(
            id=row["id"],
            title=row["title"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def list_all(self, limit: int = 50, offset: int = 0) -> list[SessionRecord]:
        cursor = self.conn.execute(
            "SELECT id, title, created_at, updated_at FROM sessions ORDER BY updated_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        return [
            SessionRecord(
                id=row["id"],
                title=row["title"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            for row in cursor.fetchall()
        ]

    def update_title(self, session_id: str, title: str) -> bool:
        now = _now_iso()
        cursor = self.conn.execute(
            "UPDATE sessions SET title = ?, updated_at = ? WHERE id = ?",
            (title, now, session_id),
        )
        self.conn.commit()
        return cursor.rowcount > 0

    def touch(self, session_id: str) -> bool:
        now = _now_iso()
        cursor = self.conn.execute(
            "UPDATE sessions SET updated_at = ? WHERE id = ?",
            (now, session_id),
        )
        self.conn.commit()
        return cursor.rowcount > 0

    def delete(self, session_id: str) -> bool:
        cursor = self.conn.execute(
            "DELETE FROM sessions WHERE id = ?",
            (session_id,),
        )
        self.conn.commit()
        return cursor.rowcount > 0


# Short alias
SessionRepo = SessionRepository
