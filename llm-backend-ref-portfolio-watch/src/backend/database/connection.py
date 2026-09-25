"""SQLite connection manager and schema initialization for Portfolio Watch V4.

Provides centralized database connection, schema migration, and table initialization
for sessions, messages, market_history_10d, hitl_evaluations, and watchlist.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

SCHEMA_SQL = """
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
    created_at TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_hitl_session_id ON hitl_evaluations(session_id);

CREATE TABLE IF NOT EXISTS watchlist (
    symbol TEXT PRIMARY KEY,
    threshold_pct REAL NOT NULL DEFAULT 3.0 CHECK (threshold_pct >= 0),
    updated_at TEXT NOT NULL
);
"""


def get_db_path() -> Path:
    """Resolve database path from environment variable SQLITE_PATH or fallback to resources/data."""
    raw = os.environ.get("SQLITE_PATH")
    if raw:
        path = Path(raw)
    else:
        # Default local development path relative to workspace root
        root = Path(__file__).resolve().parents[3]
        path = root / "resources" / "data" / "portfolio_watch.db"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def get_connection(db_path: str | Path | None = None) -> sqlite3.Connection:
    """Create a SQLite connection with foreign keys enabled and Row factory."""
    if db_path is None:
        target = get_db_path()
    else:
        target = Path(db_path)
        target.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(target), check_same_thread=False, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    init_db(conn)
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    """Execute DDL statements to ensure all required tables exist and migrate schemas."""
    conn.executescript(SCHEMA_SQL)
    # Check if reason column exists in hitl_evaluations for migration
    try:
        cursor = conn.execute("PRAGMA table_info(hitl_evaluations)")
        columns = [row["name"] for row in cursor.fetchall()]
        if "reason" not in columns:
            conn.execute("ALTER TABLE hitl_evaluations ADD COLUMN reason TEXT")
    except Exception:
        pass
    conn.commit()
