"""Kết nối PostgreSQL dùng chung cho các store trong AI Backend."""

from __future__ import annotations

import threading

from ai_backend.shared.settings import ai_settings
from common.database import PG_SCHEMA_SQL, PgConn, connect_postgres

_schema_lock = threading.Lock()
_ready_schemas: set[str] = set()


def connect(schema: str = "public") -> PgConn:
    """Mở kết nối PostgreSQL theo DATABASE_URL; tạo bảng ở lần đầu dùng schema."""
    if not ai_settings.database_url:
        raise RuntimeError("Thiếu DATABASE_URL: AI Backend chỉ dùng PostgreSQL.")
    conn = connect_postgres(ai_settings.database_url, schema=schema)
    with _schema_lock:
        if schema not in _ready_schemas:
            conn.executescript(PG_SCHEMA_SQL)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_watchlist_user_id ON watchlist(user_id)")
            conn.commit()
            _ready_schemas.add(schema)
    return conn
