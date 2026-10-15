"""Unit & Integration tests for Web Backend Database Persistence.

Verifies schema initialization, foreign keys, CRUD operations for all entities,
and persistent data retention across closed/reopened SQLite connections.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from web_backend.infra.database.connection import get_connection, init_db
from web_backend.infra.database.repositories import (
    HITLEvaluationRecord,
    HITLEvaluationRepository,
    MarketHistoryRecord,
    MarketHistoryRepository,
    MessageRecord,
    MessageRepository,
    PortfolioHoldingRecord,
    PortfolioHoldingRepository,
    SessionRecord,
    SessionRepository,
    UserSettingsRecord,
    UserSettingsRepository,
    WatchlistRecord,
    WatchlistRepository,
)


@pytest.fixture
def temp_db_path(tmp_path: Path) -> Path:
    return tmp_path / "test_persistence.db"


@pytest.fixture
def db_conn(temp_db_path: Path):
    conn = get_connection(temp_db_path)
    try:
        yield conn
    finally:
        conn.close()


def test_schema_initialization_and_foreign_keys(db_conn: sqlite3.Connection):
    """Ensure all required tables and indices are created, and foreign keys are active."""
    fk = db_conn.execute("PRAGMA foreign_keys").fetchone()[0]
    assert fk == 1, "SQLite foreign keys must be enabled"

    cursor = db_conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name ASC"
    )
    tables = {row["name"] for row in cursor.fetchall()}

    required_tables = {
        "sessions",
        "messages",
        "market_history_10d",
        "hitl_evaluations",
        "watchlist",
        "portfolio_holdings",
        "user_settings",
    }
    assert required_tables.issubset(tables), f"Missing tables: {required_tables - tables}"


def test_session_repository_crud(db_conn: sqlite3.Connection):
    repo = SessionRepository(db_conn)

    session = repo.create("Cuộc trò chuyện ban đầu", session_id="sess-crud")
    assert session.id == "sess-crud"
    assert session.title == "Cuộc trò chuyện ban đầu"

    fetched = repo.get("sess-crud")
    assert fetched is not None
    assert fetched.title == "Cuộc trò chuyện ban đầu"

    assert repo.update_title("sess-crud", "Tiêu đề đã đổi") is True
    assert repo.get("sess-crud").title == "Tiêu đề đã đổi"

    assert repo.touch("sess-crud") is True
    assert len(repo.list_all()) >= 1

    assert repo.delete("sess-crud") is True
    assert repo.get("sess-crud") is None


def test_message_repository_crud_and_cascade(db_conn: sqlite3.Connection):
    s_repo = SessionRepository(db_conn)
    m_repo = MessageRepository(db_conn)

    s = s_repo.create("Session for messages", session_id="sess-msg")
    msg = m_repo.create(
        session_id=s.id,
        role="user",
        content="Giá FPT?",
        chart_path="/charts/fpt.png",
        message_id="msg-1",
    )
    assert msg.id == "msg-1"
    assert msg.chart_path == "/charts/fpt.png"

    msgs = m_repo.list_by_session(s.id)
    assert len(msgs) == 1
    assert msgs[0].content == "Giá FPT?"

    s_repo.delete(s.id)
    assert m_repo.get("msg-1") is None
    assert len(m_repo.list_by_session(s.id)) == 0


def test_portfolio_holding_repository_crud(db_conn: sqlite3.Connection):
    repo = PortfolioHoldingRepository(db_conn)

    h = repo.create(symbol="FPT", quantity=100.0, avg_buy_price=95000.0, user_id="user_a", holding_id="hold-1")
    assert h.id == "hold-1"
    assert h.symbol == "FPT"

    assert repo.update("hold-1", quantity=150.0) is True
    fetched = repo.get("hold-1")
    assert fetched.quantity == 150.0

    items_a = repo.list_by_user("user_a")
    assert len(items_a) == 1

    assert repo.delete("hold-1", user_id="user_a") is True
    assert repo.get("hold-1") is None


def test_watchlist_repository_crud(db_conn: sqlite3.Connection):
    repo = WatchlistRepository(db_conn)

    w = repo.upsert(symbol="HPG", threshold_pct=5.0, user_id="user_a")
    assert w.symbol == "HPG"
    assert w.threshold_pct == 5.0

    assert repo.get("HPG", user_id="user_a") is not None
    assert len(repo.list_all("user_a")) == 1

    assert repo.delete("HPG", user_id="user_a") is True
    assert repo.get("HPG", user_id="user_a") is None


def test_hitl_evaluation_repository_crud(db_conn: sqlite3.Connection):
    s_repo = SessionRepository(db_conn)
    m_repo = MessageRepository(db_conn)
    h_repo = HITLEvaluationRepository(db_conn)

    s = s_repo.create("HITL test session", session_id="s-hitl")
    m = m_repo.create(session_id=s.id, role="assistant", content="Answer", message_id="m-hitl")

    rec = h_repo.create(
        message_id=m.id,
        session_id=s.id,
        is_positive=True,
        rating=5,
        feedback="Rất hài lòng",
        eval_id="e-hitl",
    )
    assert rec.id == "e-hitl"
    assert rec.is_positive is True

    fetched = h_repo.get("e-hitl")
    assert fetched is not None
    assert fetched.feedback == "Rất hài lòng"

    assert len(h_repo.list_by_session(s.id)) == 1


def test_market_history_repository_crud(db_conn: sqlite3.Connection):
    repo = MarketHistoryRepository(db_conn)

    b1 = repo.upsert_bar("VNM", "2026-10-10", 70.0, open_=69.5, high=71.0, low=69.0, volume=500000)
    assert b1.symbol == "VNM"
    assert b1.close == 70.0

    bars = [
        MarketHistoryRecord("VNM", "2026-10-11", 70.0, 72.0, 69.5, 71.5, 600000, 2.14),
        MarketHistoryRecord("VNM", "2026-10-12", 71.5, 73.0, 71.0, 72.0, 700000, 0.70),
    ]
    repo.bulk_upsert(bars)

    history = repo.get_history("VNM", limit=10)
    assert len(history) == 3
    assert history[0].trade_date == "2026-10-10"


def test_data_persistence_across_connection_reopen(temp_db_path: Path):
    """Ensure data written to SQLite persists after closing and reopening the connection."""
    conn1 = get_connection(temp_db_path)
    s_repo1 = SessionRepository(conn1)
    s_repo1.create("Persistent Session", session_id="persist-1")
    conn1.close()

    # Reopen connection
    conn2 = get_connection(temp_db_path)
    s_repo2 = SessionRepository(conn2)
    session = s_repo2.get("persist-1")
    assert session is not None
    assert session.title == "Persistent Session"
    conn2.close()
