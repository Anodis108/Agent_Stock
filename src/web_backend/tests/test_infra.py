"""Unit tests for Web Backend Infrastructure Layer (Database, Repositories, AI Client)."""

from __future__ import annotations

import sqlite3
from unittest.mock import MagicMock, patch

import pytest

from web_backend.infra.ai_client import RemoteAiClient
from web_backend.infra.database.connection import get_connection, init_db
from web_backend.infra.database.pg import PgRow, qmark, schema_name
from web_backend.infra.database.repositories import (
    HITLEvaluationRecord,
    HITLEvaluationRepository,
    HITLEvalRepo,
    MarketHistoryRecord,
    MarketHistoryRepository,
    MarketHistoryRepo,
    MessageRecord,
    MessageRepository,
    MessageRepo,
    PortfolioHoldingRecord,
    PortfolioHoldingRepository,
    PortfolioRepo,
    SessionRecord,
    SessionRepository,
    SessionRepo,
    UserSettingsRecord,
    UserSettingsRepository,
    UserSettingsRepo,
    WatchlistRecord,
    WatchlistRepository,
    WatchlistRepo,
)


@pytest.fixture
def db_conn() -> sqlite3.Connection:
    """Tạo kết nối SQLite in-memory cho test."""
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    init_db(conn)
    yield conn
    conn.close()


class TestDatabaseConnection:
    """Kiểm tra kết nối và khởi tạo cơ sở dữ liệu."""

    def test_get_connection_sqlite(self, tmp_path) -> None:
        db_file = tmp_path / "test_web.db"
        conn = get_connection(db_file)
        assert conn is not None
        # Bảng phải được tạo đầy đủ
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row["name"] for row in cursor.fetchall()}
        expected = {
            "sessions",
            "messages",
            "market_history_10d",
            "hitl_evaluations",
            "watchlist",
            "portfolio_holdings",
            "user_settings",
        }
        assert expected.issubset(tables)
        conn.close()

    def test_pg_helpers(self) -> None:
        # Test qmark conversion
        sql = "SELECT * FROM users WHERE id = ? AND name LIKE '%test%'"
        converted = qmark(sql)
        assert "%s" in converted
        assert "%%test%%" in converted

        # Test schema name generation
        s1 = schema_name("test_db")
        assert s1.startswith("t_")
        assert schema_name(None) == "public"

        # Test PgRow key and index access
        row = PgRow({"col1": "val1", "col2": "val2"})
        assert row["col1"] == "val1"
        assert row[0] == "val1"
        assert row[1] == "val2"


class TestSessionAndMessageRepositories:
    """Kiểm thử SessionRepo và MessageRepo."""

    def test_session_repo_crud(self, db_conn: sqlite3.Connection) -> None:
        repo = SessionRepo(db_conn)

        # Create
        session = repo.create(title="Phiên trò chuyện 1", session_id="sess-001")
        assert session.id == "sess-001"
        assert session.title == "Phiên trò chuyện 1"

        # Get
        fetched = repo.get("sess-001")
        assert fetched is not None
        assert fetched.id == "sess-001"

        # Update title
        updated = repo.update_title("sess-001", "Tiêu đề mới")
        assert updated is True
        assert repo.get("sess-001").title == "Tiêu đề mới"

        # Touch
        assert repo.touch("sess-001") is True

        # List all
        sessions = repo.list_all(limit=10)
        assert len(sessions) >= 1

        # Delete
        assert repo.delete("sess-001") is True
        assert repo.get("sess-001") is None

    def test_message_repo_crud_and_cascade(self, db_conn: sqlite3.Connection) -> None:
        s_repo = SessionRepo(db_conn)
        m_repo = MessageRepo(db_conn)

        session = s_repo.create(title="Session Test", session_id="sess-cascade")

        # Create messages
        msg1 = m_repo.create(
            session_id=session.id,
            role="user",
            content="Phân tích HPG",
            message_id="msg-001",
        )
        msg2 = m_repo.create(
            session_id=session.id,
            role="assistant",
            content="HPG đang có xu hướng tăng",
            message_id="msg-002",
        )

        assert msg1.id == "msg-001"
        assert msg2.id == "msg-002"

        # List by session
        messages = m_repo.list_by_session(session.id)
        assert len(messages) == 2
        assert messages[0].content == "Phân tích HPG"

        # Get
        assert m_repo.get("msg-001") is not None
        assert m_repo.get("msg-unknown") is None

        # Cascade delete
        s_repo.delete(session.id)
        assert m_repo.get("msg-001") is None
        assert len(m_repo.list_by_session(session.id)) == 0


class TestPortfolioAndWatchlistRepositories:
    """Kiểm thử PortfolioRepo, UserSettingsRepo và WatchlistRepo."""

    def test_portfolio_repo_crud(self, db_conn: sqlite3.Connection) -> None:
        repo = PortfolioRepo(db_conn)

        # Create holding for user_a
        h1 = repo.create(symbol="FPT", quantity=500, avg_buy_price=105.0, user_id="user_a")
        assert h1.symbol == "FPT"
        assert h1.quantity == 500.0

        # Create holding for user_b (multi-tenant check)
        h2 = repo.create(symbol="HPG", quantity=1000, avg_buy_price=28.0, user_id="user_b")

        # List by user
        list_a = repo.list_by_user("user_a")
        assert len(list_a) == 1
        assert list_a[0].symbol == "FPT"

        list_b = repo.list_by_user("user_b")
        assert len(list_b) == 1
        assert list_b[0].symbol == "HPG"

        # Update
        updated = repo.update(h1.id, quantity=600, avg_buy_price=110.0)
        assert updated is True
        fetched = repo.get(h1.id)
        assert fetched.quantity == 600.0
        assert fetched.avg_buy_price == 110.0

        # Delete
        assert repo.delete(h1.id, user_id="user_a") is True
        assert repo.get(h1.id) is None

    def test_user_settings_repo(self, db_conn: sqlite3.Connection) -> None:
        repo = UserSettingsRepo(db_conn)

        # Default settings when not found
        default_settings = repo.get("user_new")
        assert default_settings.alert_threshold_pct == 3.0

        # Set threshold
        saved = repo.set_threshold("user_new", 7.5)
        assert saved.alert_threshold_pct == 7.5

        # Fetch saved
        fetched = repo.get("user_new")
        assert fetched.alert_threshold_pct == 7.5

    def test_watchlist_repo_crud(self, db_conn: sqlite3.Connection) -> None:
        repo = WatchlistRepo(db_conn)

        # Upsert
        w1 = repo.upsert(symbol="VNM", threshold_pct=4.0, user_id="user_a")
        assert w1.symbol == "VNM"
        assert w1.threshold_pct == 4.0

        # Get
        fetched = repo.get("VNM", user_id="user_a")
        assert fetched is not None
        assert fetched.symbol == "VNM"

        # List
        items = repo.list_all("user_a")
        assert len(items) == 1

        # Delete
        assert repo.delete("VNM", user_id="user_a") is True
        assert repo.get("VNM", user_id="user_a") is None


class TestMarketHistoryAndHITLRepositories:
    """Kiểm thử MarketHistoryRepo và HITLEvalRepo."""

    def test_market_history_repo(self, db_conn: sqlite3.Connection) -> None:
        repo = MarketHistoryRepo(db_conn)

        # Bulk upsert bars
        bars = [
            MarketHistoryRecord("FPT", "2026-10-10", 110.0, 112.0, 109.0, 111.0, 1000000, 1.0),
            MarketHistoryRecord("FPT", "2026-10-11", 111.0, 114.0, 110.0, 113.5, 1200000, 2.25),
        ]
        repo.bulk_upsert(bars)

        # Get history
        hist = repo.get_history("FPT", limit=5)
        assert len(hist) == 2
        assert hist[0].trade_date == "2026-10-10"

        # Tracked symbols
        symbols = repo.get_tracked_symbols()
        assert "FPT" in symbols

    def test_hitl_evaluation_repo(self, db_conn: sqlite3.Connection) -> None:
        s_repo = SessionRepo(db_conn)
        m_repo = MessageRepo(db_conn)
        h_repo = HITLEvalRepo(db_conn)

        session = s_repo.create(title="Session HITL", session_id="sess-hitl")
        msg = m_repo.create(session_id=session.id, role="assistant", content="Test HITL", message_id="msg-hitl")

        eval_rec = h_repo.create(
            message_id=msg.id,
            session_id=session.id,
            is_positive=True,
            rating=5,
            feedback="Tuyệt vời",
            signal_score=1.0,
        )
        assert eval_rec.is_positive is True
        assert eval_rec.rating == 5

        # Get
        fetched = h_repo.get(eval_rec.id)
        assert fetched is not None
        assert fetched.signal_score == 1.0

        # List by session
        evals = h_repo.list_by_session(session.id)
        assert len(evals) == 1


class TestRemoteAiClient:
    """Kiểm thử RemoteAiClient."""

    def test_remote_ai_client_init(self) -> None:
        client = RemoteAiClient(base_url="http://127.0.0.1:8001", timeout=30.0)
        assert client.base_url == "http://127.0.0.1:8001"
        assert client.timeout == 30.0

    @patch("web_backend.infra.ai_client.remote_ai_client.urllib.request.urlopen")
    def test_check_health_success(self, mock_urlopen) -> None:
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"status": "ok", "service": "ai_backend"}'
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        client = RemoteAiClient()
        res = client.check_health()
        assert res.get("status") == "ok"
        assert client.is_alive() is True

    @patch("web_backend.infra.ai_client.remote_ai_client.urllib.request.urlopen")
    def test_check_health_unreachable(self, mock_urlopen) -> None:
        mock_urlopen.side_effect = Exception("Connection refused")
        client = RemoteAiClient()
        res = client.check_health()
        assert res.get("status") == "unreachable"
        assert client.is_alive() is False
