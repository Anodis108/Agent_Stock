from __future__ import annotations

from datetime import datetime, timezone
import json
import sqlite3
from typing import Any

from backend.infra.storage.sqlite_db import connect
from backend.shared.settings import settings


def parse_timestamp(ts: Any) -> datetime | None:
    """Parse various timestamp formats into a UTC-aware datetime."""
    if not ts:
        return None
    if isinstance(ts, datetime):
        return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
    if isinstance(ts, (int, float)):
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    if isinstance(ts, str):
        s = ts.strip()
        if not s:
            return None
        iso_str = s.replace(" ", "T")
        if not iso_str.endswith("Z") and "+" not in iso_str and "-" not in iso_str[10:]:
            iso_str += "Z"
        try:
            return datetime.fromisoformat(iso_str)
        except ValueError:
            pass
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
            try:
                dt = datetime.strptime(s, fmt)
                return dt.replace(tzinfo=timezone.utc)
            except ValueError:
                continue
    return None


def filter_conversation_history(
    items: list[dict[str, Any]],
    *,
    limit: int | None = None,
    ttl_minutes: int | float | None = None,
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    """Lọc danh sách hội thoại theo TTL độ tươi và sliding window.

    - Giữ thứ tự hội thoại (cũ -> mới).
    - Loại bỏ các message cũ hơn ttl_minutes khi có trường created_at hợp lệ.
    - Message không có timestamp hoặc timestamp không parse được: không loại trừ vì TTL.
    - Cắt theo sliding window: lấy tối đa `limit` message gần nhất.
    """
    if not items:
        return []

    effective_limit = (
        limit if limit is not None else settings.memory_short_term_window
    )
    if effective_limit is not None:
        effective_limit = max(int(effective_limit), 1)

    effective_ttl = (
        ttl_minutes
        if ttl_minutes is not None
        else settings.memory_short_term_ttl_minutes
    )
    effective_ttl_val = float(effective_ttl) if effective_ttl is not None else 0.0

    now_dt = now or datetime.now(timezone.utc)
    if now_dt.tzinfo is None:
        now_dt = now_dt.replace(tzinfo=timezone.utc)

    fresh: list[dict[str, Any]] = []
    for item in items:
        created_at = item.get("created_at")
        if effective_ttl_val > 0 and created_at:
            dt = parse_timestamp(created_at)
            if dt is not None:
                age_seconds = (now_dt - dt.astimezone(timezone.utc)).total_seconds()
                if age_seconds > effective_ttl_val * 60:
                    continue
        fresh.append(item)

    if effective_limit is not None and len(fresh) > effective_limit:
        fresh = fresh[-effective_limit:]

    return fresh


class SqliteMemoryStore:
    def __init__(
        self,
        db_path: str,
        *,
        default_window: int | None = None,
        default_ttl_minutes: int | float | None = None,
    ):
        self._db_path = db_path
        self._default_window = default_window
        self._default_ttl_minutes = default_ttl_minutes

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

    def append_conversation(
        self,
        user_id: str,
        role: str,
        content: str,
        *,
        created_at: str | datetime | None = None,
    ) -> None:
        with self._conn() as conn:
            if created_at is not None:
                if isinstance(created_at, datetime):
                    if created_at.tzinfo:
                        created_at_str = created_at.astimezone(timezone.utc).strftime(
                            "%Y-%m-%d %H:%M:%S"
                        )
                    else:
                        created_at_str = created_at.strftime("%Y-%m-%d %H:%M:%S")
                else:
                    created_at_str = str(created_at)
                conn.execute(
                    "INSERT INTO conversations (user_id, role, content, created_at) VALUES (?, ?, ?, ?)",
                    (user_id, role, content, created_at_str),
                )
            else:
                conn.execute(
                    "INSERT INTO conversations (user_id, role, content) VALUES (?, ?, ?)",
                    (user_id, role, content),
                )
            conn.commit()

    def list_conversation(
        self,
        user_id: str,
        limit: int | None = None,
        *,
        ttl_minutes: int | float | None = None,
        now: datetime | None = None,
    ) -> list[dict[str, Any]]:
        effective_limit = (
            limit
            if limit is not None
            else (
                self._default_window
                if self._default_window is not None
                else settings.memory_short_term_window
            )
        )
        if effective_limit is not None:
            effective_limit = max(int(effective_limit), 1)

        effective_ttl = (
            ttl_minutes
            if ttl_minutes is not None
            else (
                self._default_ttl_minutes
                if self._default_ttl_minutes is not None
                else settings.memory_short_term_ttl_minutes
            )
        )
        effective_ttl_val = float(effective_ttl) if effective_ttl is not None else 0.0

        fetch_limit = (
            max((effective_limit or 20) * 10, 200)
            if effective_ttl_val > 0
            else (effective_limit or 20)
        )

        with self._conn() as conn:
            rows = conn.execute(
                "SELECT role, content, created_at FROM conversations "
                "WHERE user_id = ? ORDER BY id DESC LIMIT ?",
                (user_id, max(fetch_limit, 1)),
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
        return filter_conversation_history(
            items,
            limit=effective_limit,
            ttl_minutes=effective_ttl,
            now=now,
        )

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
