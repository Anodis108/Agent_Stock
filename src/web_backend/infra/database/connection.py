"""Kết nối PostgreSQL và khởi tạo schema cho Web Backend (chỉ dùng PostgreSQL qua DATABASE_URL)."""

from __future__ import annotations

import threading

from common.database import PG_SCHEMA_SQL, PgConn, connect_postgres
from web_backend.shared.settings import web_settings

# Schema dùng chung với ai_backend; test đổi sang schema tạm để cô lập dữ liệu
DEFAULT_SCHEMA = "public"

_schema_lock = threading.Lock()
_ready_schemas: set[str] = set()


def get_connection(schema: str | None = None) -> PgConn:
    """Mở kết nối PostgreSQL theo DATABASE_URL; tạo bảng ở lần đầu dùng schema."""
    if not web_settings.database_url:
        raise RuntimeError("Thiếu DATABASE_URL: Web Backend chỉ dùng PostgreSQL.")
    target = schema or DEFAULT_SCHEMA
    conn = connect_postgres(web_settings.database_url, schema=target)
    with _schema_lock:
        if target not in _ready_schemas:
            init_db(conn)
            _ready_schemas.add(target)
    return conn


def init_db(conn: PgConn) -> None:
    """Tạo bảng session, tin nhắn, watchlist, danh mục, HITL và các bảng liên quan."""
    conn.executescript(PG_SCHEMA_SQL)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_watchlist_user_id ON watchlist(user_id)")
    conn.commit()


__all__ = [
    "DEFAULT_SCHEMA",
    "get_connection",
    "init_db",
]
