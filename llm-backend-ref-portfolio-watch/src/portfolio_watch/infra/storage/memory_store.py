from __future__ import annotations

import json
import sqlite3
from typing import Any

from src.portfolio_watch.infra.storage.sqlite_db import connect


class SqliteMemoryStore:
    def __init__(self, db_path: str):
        self._db_path = db_path

    def _conn(self) -> sqlite3.Connection:
        return connect(self._db_path)

    def read_preferences(self, user_id: str = "default") -> dict[str, Any]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT data_json FROM preferences WHERE user_id = ?",
                (user_id,),
            ).fetchone()
        if row is None:
            return {}
        try:
            data = json.loads(row["data_json"])
            return data if isinstance(data, dict) else {}
        except json.JSONDecodeError:
            return {}

    def write_preferences(self, user_id: str, preferences: dict[str, Any]) -> None:
        payload = json.dumps(preferences, ensure_ascii=False)
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO preferences (user_id, data_json) VALUES (?, ?) "
                "ON CONFLICT(user_id) DO UPDATE SET data_json = excluded.data_json",
                (user_id, payload),
            )
            conn.commit()

    def append_conversation(self, user_id: str, role: str, content: str) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO conversations (user_id, role, content) VALUES (?, ?, ?)",
                (user_id, role, content),
            )
            conn.commit()

    def list_conversation(
        self, user_id: str, limit: int = 20
    ) -> list[dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT role, content, created_at FROM conversations "
                "WHERE user_id = ? ORDER BY id DESC LIMIT ?",
                (user_id, max(limit, 1)),
            ).fetchall()
        items = [
            {
                "role": r["role"],
                "content": r["content"],
                "created_at": r["created_at"],
            }
            for r in rows
        ]
        items.reverse()
        return items

    def append_alert_event(self, user_id: str, event: dict[str, Any]) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO alert_events (user_id, event_json) VALUES (?, ?)",
                (user_id, json.dumps(event, ensure_ascii=False)),
            )
            conn.commit()

    def list_alert_events(
        self, user_id: str, limit: int = 20
    ) -> list[dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT event_json, created_at FROM alert_events "
                "WHERE user_id = ? ORDER BY id DESC LIMIT ?",
                (user_id, max(limit, 1)),
            ).fetchall()
        out: list[dict[str, Any]] = []
        for r in rows:
            try:
                event = json.loads(r["event_json"])
            except json.JSONDecodeError:
                event = {"raw": r["event_json"]}
            if isinstance(event, dict):
                event = {**event, "created_at": r["created_at"]}
                out.append(event)
            else:
                out.append({"event": event, "created_at": r["created_at"]})
        out.reverse()
        return out

    def record_rejection(
        self,
        user_id: str,
        *,
        gate: str,
        reason: str,
        context: dict[str, Any] | None = None,
    ) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO rejections (user_id, gate, reason, context_json) "
                "VALUES (?, ?, ?, ?)",
                (
                    user_id,
                    gate,
                    reason,
                    json.dumps(context or {}, ensure_ascii=False),
                ),
            )
            conn.commit()

    def list_rejections(
        self, user_id: str, limit: int = 20
    ) -> list[dict[str, Any]]:
        """Đọc lý do reject đã ghi (HITL) — helper concrete, không nằm trên Protocol."""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT gate, reason, context_json, created_at FROM rejections "
                "WHERE user_id = ? ORDER BY id DESC LIMIT ?",
                (user_id, max(limit, 1)),
            ).fetchall()
        out: list[dict[str, Any]] = []
        for r in rows:
            try:
                context = json.loads(r["context_json"] or "{}")
            except json.JSONDecodeError:
                context = {}
            out.append(
                {
                    "gate": r["gate"],
                    "reason": r["reason"],
                    "context": context if isinstance(context, dict) else {},
                    "created_at": r["created_at"],
                }
            )
        out.reverse()
        return out
