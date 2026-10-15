"""PostgreSQL and SQLite connection and schema management for Web Backend.

Handles:
- PostgreSQL with psycopg3 when DATABASE_URL is configured and reachable
- Seamless SQLite fallback for local development and offline testing
- Automatic table, index creation and column migrations
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any

from web_backend.infra.database.pg import PgConn, connect_postgres, schema_name

SQLITE_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    chart_path TEXT,
    trace_data TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id);

CREATE TABLE IF NOT EXISTS market_history_10d (
    symbol TEXT NOT NULL,
    trade_date TEXT NOT NULL,
    open REAL,
    high REAL,
    low REAL,
    close REAL NOT NULL,
    volume INTEGER,
    change_pct REAL,
    PRIMARY KEY (symbol, trade_date)
);
CREATE INDEX IF NOT EXISTS idx_market_history_symbol ON market_history_10d(symbol);

CREATE TABLE IF NOT EXISTS hitl_evaluations (
    id TEXT PRIMARY KEY,
    message_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    rating INTEGER CHECK (rating IS NULL OR (rating >= 1 AND rating <= 5)),
    feedback TEXT,
    is_positive INTEGER NOT NULL CHECK (is_positive IN (0, 1)),
    reason TEXT,
    question TEXT,
    answer TEXT,
    signal_score REAL,
    feedback_source TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_hitl_session_id ON hitl_evaluations(session_id);

CREATE TABLE IF NOT EXISTS watchlist (
    symbol TEXT NOT NULL,
    user_id TEXT NOT NULL DEFAULT 'default',
    threshold_pct REAL NOT NULL DEFAULT 3.0 CHECK (threshold_pct >= 0),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (user_id, symbol)
);

CREATE TABLE IF NOT EXISTS portfolio_holdings (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL DEFAULT 'default',
    symbol TEXT NOT NULL,
    quantity REAL NOT NULL CHECK (quantity > 0),
    avg_buy_price REAL NOT NULL CHECK (avg_buy_price >= 0),
    purchase_date TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_holdings_user_id ON portfolio_holdings(user_id);
CREATE INDEX IF NOT EXISTS idx_holdings_user_symbol ON portfolio_holdings(user_id, symbol);

CREATE TABLE IF NOT EXISTS user_settings (
    user_id TEXT PRIMARY KEY,
    alert_threshold_pct REAL NOT NULL DEFAULT 3.0 CHECK (alert_threshold_pct >= 0),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS preferences (
    user_id TEXT PRIMARY KEY,
    data_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS approvals (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    gate TEXT NOT NULL DEFAULT 'gate1',
    status TEXT NOT NULL DEFAULT 'pending',
    reason TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS last_quotes (
    user_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    price REAL,
    change_pct REAL,
    route TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL,
    PRIMARY KEY (user_id, symbol)
);

CREATE TABLE IF NOT EXISTS price_history (
    symbol TEXT NOT NULL,
    date TEXT NOT NULL,
    close REAL NOT NULL,
    open_price REAL,
    high REAL,
    low REAL,
    volume REAL,
    PRIMARY KEY (symbol, date)
);

CREATE TABLE IF NOT EXISTS alert_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    event_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS rejections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    gate TEXT NOT NULL,
    reason TEXT NOT NULL,
    context_json TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

PG_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    chart_path TEXT,
    trace_data TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id);

CREATE TABLE IF NOT EXISTS market_history_10d (
    symbol TEXT NOT NULL,
    trade_date TEXT NOT NULL,
    open REAL,
    high REAL,
    low REAL,
    close REAL NOT NULL,
    volume INTEGER,
    change_pct REAL,
    PRIMARY KEY (symbol, trade_date)
);
CREATE INDEX IF NOT EXISTS idx_market_history_symbol ON market_history_10d(symbol);

CREATE TABLE IF NOT EXISTS hitl_evaluations (
    id TEXT PRIMARY KEY,
    message_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    rating INTEGER CHECK (rating IS NULL OR (rating >= 1 AND rating <= 5)),
    feedback TEXT,
    is_positive INTEGER NOT NULL CHECK (is_positive IN (0, 1)),
    reason TEXT,
    question TEXT,
    answer TEXT,
    signal_score REAL,
    feedback_source TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_hitl_session_id ON hitl_evaluations(session_id);

CREATE TABLE IF NOT EXISTS watchlist (
    symbol TEXT NOT NULL,
    user_id TEXT NOT NULL DEFAULT 'default',
    threshold_pct REAL NOT NULL DEFAULT 3.0 CHECK (threshold_pct >= 0),
    updated_at TEXT NOT NULL DEFAULT to_char(CURRENT_TIMESTAMP, 'YYYY-MM-DD HH24:MI:SS'),
    PRIMARY KEY (user_id, symbol)
);

CREATE TABLE IF NOT EXISTS portfolio_holdings (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL DEFAULT 'default',
    symbol TEXT NOT NULL,
    quantity REAL NOT NULL CHECK (quantity > 0),
    avg_buy_price REAL NOT NULL CHECK (avg_buy_price >= 0),
    purchase_date TEXT,
    created_at TEXT NOT NULL DEFAULT to_char(CURRENT_TIMESTAMP, 'YYYY-MM-DD HH24:MI:SS'),
    updated_at TEXT NOT NULL DEFAULT to_char(CURRENT_TIMESTAMP, 'YYYY-MM-DD HH24:MI:SS')
);
CREATE INDEX IF NOT EXISTS idx_holdings_user_id ON portfolio_holdings(user_id);
CREATE INDEX IF NOT EXISTS idx_holdings_user_symbol ON portfolio_holdings(user_id, symbol);

CREATE TABLE IF NOT EXISTS user_settings (
    user_id TEXT PRIMARY KEY,
    alert_threshold_pct REAL NOT NULL DEFAULT 3.0 CHECK (alert_threshold_pct >= 0),
    updated_at TEXT NOT NULL DEFAULT to_char(CURRENT_TIMESTAMP, 'YYYY-MM-DD HH24:MI:SS')
);

CREATE TABLE IF NOT EXISTS conversations (
    id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    user_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT to_char(CURRENT_TIMESTAMP, 'YYYY-MM-DD HH24:MI:SS')
);

CREATE TABLE IF NOT EXISTS preferences (
    user_id TEXT PRIMARY KEY,
    data_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS approvals (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    gate TEXT NOT NULL DEFAULT 'gate1',
    status TEXT NOT NULL DEFAULT 'pending',
    reason TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS last_quotes (
    user_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    price DOUBLE PRECISION,
    change_pct DOUBLE PRECISION,
    route TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL,
    PRIMARY KEY (user_id, symbol)
);

CREATE TABLE IF NOT EXISTS price_history (
    symbol TEXT NOT NULL,
    date TEXT NOT NULL,
    close DOUBLE PRECISION NOT NULL,
    open_price DOUBLE PRECISION,
    high DOUBLE PRECISION,
    low DOUBLE PRECISION,
    volume DOUBLE PRECISION,
    PRIMARY KEY (symbol, date)
);

CREATE TABLE IF NOT EXISTS alert_events (
    id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    user_id TEXT NOT NULL,
    event_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT to_char(CURRENT_TIMESTAMP, 'YYYY-MM-DD HH24:MI:SS')
);

CREATE TABLE IF NOT EXISTS rejections (
    id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    user_id TEXT NOT NULL,
    gate TEXT NOT NULL,
    reason TEXT NOT NULL,
    context_json TEXT,
    created_at TEXT NOT NULL DEFAULT to_char(CURRENT_TIMESTAMP, 'YYYY-MM-DD HH24:MI:SS')
);
"""

SCHEMA_SQL = SQLITE_SCHEMA_SQL


def _database_url() -> str:
    url = os.environ.get("DATABASE_URL", "").strip()
    if url:
        return url
    try:
        from common.settings.secrets import get_secret
        sec = get_secret("DATABASE_URL")
        if sec:
            return sec.strip()
    except Exception:
        pass
    try:
        from web_backend.shared.settings import settings
        url = (settings.database_url or "").strip()
    except Exception:
        pass
    return url


def get_db_path() -> Path:
    raw = os.environ.get("SQLITE_PATH", "").strip()
    if raw:
        return Path(raw)
    root = None
    p = Path(__file__).resolve().parent
    for _ in range(6):
        if (p / "pyproject.toml").is_file():
            root = p
            break
        p = p.parent
    if root is None:
        root = Path(__file__).resolve().parents[4]
    path = root / "resources" / "data" / "portfolio_watch.db"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def get_connection(db_path: str | Path | None = None) -> Any:
    """Mở kết nối tới PostgreSQL nếu có cấu hình và kết nối được; ngược lại fallback sang SQLite."""
    target = Path(db_path) if db_path is not None else get_db_path()
    use_sqlite_explicit = (
        db_path is not None
        and (
            str(db_path).endswith(".db")
            or str(db_path).endswith(".sqlite")
            or str(db_path) == ":memory:"
        )
    ) or bool(os.environ.get("SQLITE_PATH", "").strip())

    if use_sqlite_explicit:
        target.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(target), check_same_thread=False, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        init_db(conn)
        return conn

    url = _database_url()
    if url:
        try:
            conn = connect_postgres(url, schema=schema_name(target))
            init_db(conn)
            return conn
        except Exception:
            pass

    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(target), check_same_thread=False, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    init_db(conn)
    return conn


def init_db(conn: Any) -> None:
    """Tạo bảng session, tin nhắn, watchlist, danh mục, HITL và các bảng liên quan."""
    if isinstance(conn, sqlite3.Connection):
        conn.executescript(SQLITE_SCHEMA_SQL)
        try:
            cursor = conn.execute("PRAGMA table_info(hitl_evaluations)")
            columns = [row["name"] for row in cursor.fetchall()]
            if columns:
                if "reason" not in columns:
                    conn.execute("ALTER TABLE hitl_evaluations ADD COLUMN reason TEXT")
                if "question" not in columns:
                    conn.execute("ALTER TABLE hitl_evaluations ADD COLUMN question TEXT")
                if "answer" not in columns:
                    conn.execute("ALTER TABLE hitl_evaluations ADD COLUMN answer TEXT")
                if "signal_score" not in columns:
                    conn.execute("ALTER TABLE hitl_evaluations ADD COLUMN signal_score REAL")
                if "feedback_source" not in columns:
                    conn.execute("ALTER TABLE hitl_evaluations ADD COLUMN feedback_source TEXT")
        except Exception:
            pass
        try:
            cursor = conn.execute("PRAGMA table_info(watchlist)")
            columns = [row["name"] for row in cursor.fetchall()]
            if columns:
                if "user_id" not in columns:
                    conn.execute("ALTER TABLE watchlist ADD COLUMN user_id TEXT NOT NULL DEFAULT 'default'")
                if "updated_at" not in columns:
                    conn.execute("ALTER TABLE watchlist ADD COLUMN updated_at TEXT NOT NULL DEFAULT (datetime('now'))")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_watchlist_user_id ON watchlist(user_id)")
        except Exception:
            pass
        conn.commit()
    else:
        conn.executescript(PG_SCHEMA_SQL)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_watchlist_user_id ON watchlist(user_id)")
        conn.commit()
