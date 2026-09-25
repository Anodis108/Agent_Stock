"""Unit tests for Phase 2: Core Backend & Database Persistence.

Verifies schema initialization, foreign keys, CRUD operations for all entities,
and persistent data retention across closed/reopened SQLite connections.
"""

from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

import pytest

from backend.database.connection import get_connection, init_db
from backend.database.repositories import (
    HITLEvaluationRecord,
    HITLEvaluationRepository,
    MarketHistoryRecord,
    MarketHistoryRepository,
    MessageRecord,
    MessageRepository,
    SessionRecord,
    SessionRepository,
    WatchlistRecord,
    WatchlistRepository,
)


@pytest.fixture
def temp_db_path(tmp_path: Path) -> Path:
    """Fixture providing a clean SQLite file path."""
    return tmp_path / "test_persistence.db"


@pytest.fixture
def db_conn(temp_db_path: Path):
    """Fixture providing an open database connection to the temp DB."""
    conn = get_connection(temp_db_path)
    try:
        yield conn
    finally:
        conn.close()


def test_schema_initialization_and_foreign_keys(db_conn: sqlite3.Connection):
    """Ensure all required tables and indices are created, and foreign keys are active."""
    # Check foreign keys enabled
    fk = db_conn.execute("PRAGMA foreign_keys").fetchone()[0]
    assert fk == 1, "SQLite foreign keys must be enabled"

    # Check table names
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
    }
    assert required_tables.issubset(tables), f"Missing tables: {required_tables - tables}"


def test_session_repository_crud(db_conn: sqlite3.Connection):
    """Test Session creation, lookup, listing, title update, touch, and deletion."""
    repo = SessionRepository(db_conn)

    # 1. Create
    s1 = repo.create(title="Phân tích cổ phiếu FPT")
    assert s1.id is not None
    assert s1.title == "Phân tích cổ phiếu FPT"

    s2 = repo.create(title="So sánh VNM và HPG")
    assert s2.id != s1.id

    # 2. Get
    fetched = repo.get(s1.id)
    assert fetched is not None
    assert fetched.id == s1.id
    assert fetched.title == "Phân tích cổ phiếu FPT"

    assert repo.get("non-existent-id") is None

    # 3. List
    all_sessions = repo.list_all()
    assert len(all_sessions) >= 2
    session_ids = [s.id for s in all_sessions]
    assert s1.id in session_ids and s2.id in session_ids

    # 4. Update Title
    ok = repo.update_title(s1.id, "Phân tích chuyên sâu FPT Q3")
    assert ok is True
    updated = repo.get(s1.id)
    assert updated.title == "Phân tích chuyên sâu FPT Q3"

    # 5. Touch
    assert repo.touch(s1.id) is True

    # 6. Delete
    deleted = repo.delete(s2.id)
    assert deleted is True
    assert repo.get(s2.id) is None


def test_message_repository_crud_and_cascade(db_conn: sqlite3.Connection):
    """Test Message creation, listing by session, ordering, and cascade delete."""
    s_repo = SessionRepository(db_conn)
    m_repo = MessageRepository(db_conn)

    session = s_repo.create(title="Chat Session 1")

    # 1. Create messages
    m1 = m_repo.create(
        session_id=session.id,
        role="user",
        content="Giá FPT hôm nay bao nhiêu?",
    )
    assert m1.id is not None
    assert m1.role == "user"

    m2 = m_repo.create(
        session_id=session.id,
        role="assistant",
        content="FPT đóng cửa ở mức 135.000 VNĐ (+1.5%).",
        chart_path="/static/charts/fpt.png",
        trace_data='{"agent": "price_agent"}',
    )
    assert m2.chart_path == "/static/charts/fpt.png"
    assert m2.trace_data == '{"agent": "price_agent"}'

    # 2. List by session
    messages = m_repo.list_by_session(session.id)
    assert len(messages) == 2
    assert messages[0].id == m1.id
    assert messages[1].id == m2.id

    # 3. Get single message
    fetched = m_repo.get(m2.id)
    assert fetched is not None
    assert fetched.content == "FPT đóng cửa ở mức 135.000 VNĐ (+1.5%)."

    # 4. Cascade delete: deleting the session must delete all messages
    s_repo.delete(session.id)
    assert m_repo.get(m1.id) is None
    assert m_repo.get(m2.id) is None
    assert len(m_repo.list_by_session(session.id)) == 0


def test_market_history_repository_10d(db_conn: sqlite3.Connection):
    """Test upserting daily price bars, conflict handling, and fetching latest 10 days."""
    repo = MarketHistoryRepository(db_conn)

    # 1. Insert 12 trading days for FPT
    dates = [f"2026-09-{i:02d}" for i in range(1, 13)]
    for i, d in enumerate(dates):
        repo.upsert_bar(
            symbol="FPT",
            trade_date=d,
            open_=130.0 + i,
            high=132.0 + i,
            low=129.0 + i,
            close=131.0 + i,
            volume=1000000 + i * 50000,
            change_pct=1.0,
        )

    # 2. Fetch history with limit 10
    history_asc = repo.get_history("FPT", limit=10, ascending=True)
    assert len(history_asc) == 10
    # Should contain the latest 10 dates (Sept 3 to Sept 12)
    assert history_asc[0].trade_date == "2026-09-03"
    assert history_asc[-1].trade_date == "2026-09-12"

    history_desc = repo.get_history("FPT", limit=10, ascending=False)
    assert len(history_desc) == 10
    assert history_desc[0].trade_date == "2026-09-12"
    assert history_desc[-1].trade_date == "2026-09-03"

    # 3. Upsert on conflict (update close price of 2026-09-12)
    repo.upsert_bar(
        symbol="FPT",
        trade_date="2026-09-12",
        close=145.0,
        change_pct=5.2,
    )
    latest = repo.get_history("FPT", limit=1, ascending=False)
    assert len(latest) == 1
    assert latest[0].close == 145.0
    assert latest[0].change_pct == 5.2

    # 4. Bulk upsert and tracked symbols
    vnm_bars = [
        MarketHistoryRecord(
            symbol="VNM",
            trade_date=d,
            open=70.0,
            high=71.0,
            low=69.5,
            close=70.5,
            volume=500000,
            change_pct=0.5,
        )
        for d in dates[:5]
    ]
    repo.bulk_upsert(vnm_bars)
    symbols = repo.get_tracked_symbols()
    assert "FPT" in symbols
    assert "VNM" in symbols


def test_hitl_evaluation_repository_crud(db_conn: sqlite3.Connection):
    """Test HITL evaluation creation, star rating 1-5, feedback text, and cascade delete."""
    s_repo = SessionRepository(db_conn)
    m_repo = MessageRepository(db_conn)
    h_repo = HITLEvaluationRepository(db_conn)

    session = s_repo.create(title="HITL Test Session")
    msg = m_repo.create(
        session_id=session.id,
        role="assistant",
        content="Khuyến nghị theo dõi vùng giá 130.",
    )

    # 1. Create positive rating
    eval1 = h_repo.create(
        message_id=msg.id,
        session_id=session.id,
        is_positive=True,
        rating=5,
        feedback="Phân tích rất chuẩn xác!",
    )
    assert eval1.id is not None
    assert eval1.is_positive is True
    assert eval1.rating == 5
    assert eval1.feedback == "Phân tích rất chuẩn xác!"

    # 2. Get and list
    fetched = h_repo.get(eval1.id)
    assert fetched is not None
    assert fetched.rating == 5
    assert fetched.is_positive is True

    session_evals = h_repo.list_by_session(session.id)
    assert len(session_evals) == 1
    assert session_evals[0].id == eval1.id

    # 3. Create negative rating
    eval2 = h_repo.create(
        message_id=msg.id,
        session_id=session.id,
        is_positive=False,
        rating=2,
        feedback="Thiếu thông tin khối lượng giao dịch.",
    )
    assert eval2.is_positive is False
    assert len(h_repo.list_by_session(session.id)) == 2

    # 4. Cascade delete with session
    s_repo.delete(session.id)
    assert h_repo.get(eval1.id) is None
    assert h_repo.get(eval2.id) is None


def test_watchlist_repository_crud(db_conn: sqlite3.Connection):
    """Test Watchlist upsert, default threshold, update, and deletion."""
    repo = WatchlistRepository(db_conn)

    # 1. Upsert
    w1 = repo.upsert("FPT", threshold_pct=2.5)
    assert w1.symbol == "FPT"
    assert w1.threshold_pct == 2.5

    w2 = repo.upsert("vnm")  # lower-case should be normalized to uppercase
    assert w2.symbol == "VNM"
    assert w2.threshold_pct == 3.0

    # 2. Get
    fetched = repo.get("fpt")
    assert fetched is not None
    assert fetched.symbol == "FPT"
    assert fetched.threshold_pct == 2.5

    # 3. Update existing threshold
    w1_updated = repo.upsert("FPT", threshold_pct=4.0)
    assert w1_updated.threshold_pct == 4.0
    assert repo.get("FPT").threshold_pct == 4.0

    # 4. List all
    all_items = repo.list_all()
    symbols = [item.symbol for item in all_items]
    assert "FPT" in symbols and "VNM" in symbols

    # 5. Delete
    assert repo.delete("VNM") is True
    assert repo.get("VNM") is None


def test_data_persistence_across_connections(temp_db_path: Path):
    """Crucial Acceptance Criteria: Data written to SQLite persists after closing and reopening connection."""
    # Phase 1: Open conn1, write records into all tables, then close conn1
    conn1 = get_connection(temp_db_path)
    s_repo1 = SessionRepository(conn1)
    m_repo1 = MessageRepository(conn1)
    mh_repo1 = MarketHistoryRepository(conn1)
    h_repo1 = HITLEvaluationRepository(conn1)
    w_repo1 = WatchlistRepository(conn1)

    session = s_repo1.create(title="Persistent Research Session")
    msg = m_repo1.create(
        session_id=session.id,
        role="assistant",
        content="Báo cáo tài chính quý 3 của HPG.",
        chart_path="/charts/hpg_q3.png",
    )
    mh_repo1.upsert_bar(
        symbol="HPG",
        trade_date="2026-09-22",
        close=28.5,
        volume=15000000,
        change_pct=2.1,
    )
    eval_rec = h_repo1.create(
        message_id=msg.id,
        session_id=session.id,
        is_positive=True,
        rating=5,
        feedback="Tuyệt vời!",
    )
    w_repo1.upsert("HPG", threshold_pct=3.5)

    # Explicitly close connection 1
    conn1.close()

    # Phase 2: Open conn2 to the exact same file path, verify all data remains intact
    conn2 = get_connection(temp_db_path)
    try:
        s_repo2 = SessionRepository(conn2)
        m_repo2 = MessageRepository(conn2)
        mh_repo2 = MarketHistoryRepository(conn2)
        h_repo2 = HITLEvaluationRepository(conn2)
        w_repo2 = WatchlistRepository(conn2)

        # Verify Session
        s_fetched = s_repo2.get(session.id)
        assert s_fetched is not None
        assert s_fetched.title == "Persistent Research Session"

        # Verify Message
        messages = m_repo2.list_by_session(session.id)
        assert len(messages) == 1
        assert messages[0].id == msg.id
        assert messages[0].content == "Báo cáo tài chính quý 3 của HPG."
        assert messages[0].chart_path == "/charts/hpg_q3.png"

        # Verify Market History
        history = mh_repo2.get_history("HPG", limit=10)
        assert len(history) == 1
        assert history[0].symbol == "HPG"
        assert history[0].close == 28.5
        assert history[0].change_pct == 2.1

        # Verify HITL Evaluation
        eval_fetched = h_repo2.get(eval_rec.id)
        assert eval_fetched is not None
        assert eval_fetched.rating == 5
        assert eval_fetched.feedback == "Tuyệt vời!"
        assert eval_fetched.is_positive is True

        # Verify Watchlist
        w_fetched = w_repo2.get("HPG")
        assert w_fetched is not None
        assert w_fetched.threshold_pct == 3.5

    finally:
        conn2.close()
