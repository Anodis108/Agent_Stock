"""Unit & Integration tests for PortfolioWatchAgent (Phase 2).

Verifies portfolio P&L / NAV inquiries and watchlist tracking across multiple users,
preventing spurious ticker extraction (TRA, NAV, XEM).
"""

from __future__ import annotations

import sqlite3
import pytest

from backend.agents.portfolio_watch_agent import run_portfolio_watch_agent
from backend.agents.supervisor_agent.nodes import (
    HeuristicRewriteBrain,
    HeuristicSupervisorBrain,
    _extract_symbols,
)
from backend.database.connection import init_db
from backend.database.repositories import (
    PortfolioHoldingRepository,
    UserSettingsRepository,
)
from backend.domain.entities import WatchlistItem
from backend.domain.ports import PriceBar, PriceQuote, PriceSourcePort
from backend.graph.chat import run_chat_graph
from backend.infra.storage.watchlist_store import SqliteWatchlistStore


class MockPriceSource(PriceSourcePort):
    def __init__(self, quotes: dict[str, float | None] | None = None) -> None:
        self.quotes = quotes or {
            "FPT": 125.0,
            "HPG": 28.0,
            "VNM": 75.0,
        }

    def fetch_latest_close(self, symbol: str) -> PriceQuote:
        sym = symbol.upper()
        if sym in self.quotes:
            val = self.quotes[sym]
            if val is None:
                return PriceQuote(symbol=sym, latest_close=None, error="Symbol not found")
            return PriceQuote(symbol=sym, latest_close=val, prev_close=val)
        return PriceQuote(symbol=sym, latest_close=None, error="No quote available")

    def fetch_history(self, symbol: str, lookback_days: int = 14) -> list[PriceBar]:
        return []


class DummyNewsSource:
    pass


class DummyHistoryStore:
    pass


class DummyMemoryStore:
    def __init__(self):
        self._conv = []

    def read_preferences(self, user_id: str = "default"):
        return {}

    def write_preferences(self, user_id: str, preferences: dict):
        pass

    def append_conversation(self, user_id: str, role: str, content: str, *, created_at: str | None = None):
        self._conv.append({"role": role, "content": content})

    def list_conversation(self, user_id: str, limit: int | None = None, *, ttl_minutes: int | float | None = None):
        return list(self._conv)

    def append_alert_event(self, user_id: str, event: dict):
        pass


@pytest.fixture
def test_db_path(tmp_path):
    db_file = tmp_path / "test_portfolio.db"
    conn = sqlite3.connect(str(db_file))
    conn.row_factory = sqlite3.Row
    init_db(conn)
    conn.close()
    return str(db_file)


# ==============================================================================
# 1. Unit Tests: Ticker stopword filtering for Vietnamese phrases
# ==============================================================================

def test_no_spurious_tickers_in_portfolio_queries():
    """Confirms that 'Kiểm tra' does not produce 'TRA', 'NAV' does not produce 'NAV', 'Xem' does not produce 'XEM'."""
    q1 = "Kiểm tra hiệu suất P&L và tổng giá trị NAV của danh mục hiện tại"
    syms1 = _extract_symbols(q1)
    assert "TRA" not in syms1, "Kiểm tra không được nhận nhầm thành mã TRA!"
    assert "NAV" not in syms1, "NAV không được nhận nhầm thành mã NAV!"

    q2 = "Xem các mã trong danh sách theo dõi kèm ngưỡng cảnh báo biến động"
    syms2 = _extract_symbols(q2)
    assert "XEM" not in syms2, "Xem không được nhận nhầm thành mã XEM!"


# ==============================================================================
# 2. Supervisor Routing Tests for Portfolio & Watchlist
# ==============================================================================

def test_supervisor_routes_portfolio_intent():
    """Supervisor correctly identifies portfolio intent and routes to portfolio_watch."""
    rewriter = HeuristicRewriteBrain()
    supervisor = HeuristicSupervisorBrain()

    rw = rewriter.rewrite("Danh mục đầu tư của tôi đang lãi hay lỗ như thế nào?", [])
    assert rw.intent == "portfolio"
    assert rw.symbols == []

    decision = supervisor.route(rw)
    assert "portfolio_watch" in decision.agents_to_call


def test_supervisor_routes_watchlist_intent():
    """Supervisor correctly identifies watchlist intent and routes to portfolio_watch."""
    rewriter = HeuristicRewriteBrain()
    supervisor = HeuristicSupervisorBrain()

    rw = rewriter.rewrite("Xem các mã trong danh sách theo dõi kèm ngưỡng cảnh báo biến động", [])
    assert rw.intent == "watchlist"
    assert rw.symbols == []

    decision = supervisor.route(rw)
    assert "portfolio_watch" in decision.agents_to_call


# ==============================================================================
# 3. PortfolioWatchAgent Unit Tests (Empty & Populated States, Isolation)
# ==============================================================================

def test_portfolio_watch_agent_empty(test_db_path, monkeypatch):
    """When a user has no holdings, returns a clean informative markdown message."""
    from backend.shared.settings import settings
    monkeypatch.setenv("SQLITE_PATH", test_db_path)
    monkeypatch.setattr(settings, "sqlite_path", test_db_path)

    store = SqliteWatchlistStore(test_db_path)
    price_source = MockPriceSource()

    res = run_portfolio_watch_agent(
        user_id="user_empty",
        intent="all",
        price_source=price_source,
        watchlist_store=store,
    )
    assert res.user_id == "user_empty"
    assert "Danh mục hiện chưa có cổ phiếu nào" in res.formatted_markdown
    assert "Danh sách theo dõi của bạn hiện đang trống" in res.formatted_markdown
    assert "nên mua" not in res.formatted_markdown.lower()
    assert "nên bán" not in res.formatted_markdown.lower()


def test_portfolio_watch_agent_with_data_and_multi_tenant(test_db_path, monkeypatch):
    """Verifies holdings & watchlist calculation and strict multi-tenant isolation."""
    from backend.shared.settings import settings
    monkeypatch.setenv("SQLITE_PATH", test_db_path)
    monkeypatch.setattr(settings, "sqlite_path", test_db_path)

    # 1. Thiết lập dữ liệu cho user_a: 1000 FPT giá 100.0, Watchlist FPT ±3%
    conn = sqlite3.connect(test_db_path)
    conn.row_factory = sqlite3.Row
    h_repo = PortfolioHoldingRepository(conn)
    u_repo = UserSettingsRepository(conn)
    h_repo.create("FPT", 1000, 100.0, user_id="user_a")
    u_repo.set_threshold("user_a", 3.0)
    conn.commit()
    conn.close()

    store = SqliteWatchlistStore(test_db_path)
    store.upsert(WatchlistItem(user_id="user_a", symbol="FPT", threshold_pct=3.0))

    # 2. Thiết lập dữ liệu cho user_b: 500 VNM giá 80.0, Watchlist VNM ±5%
    conn = sqlite3.connect(test_db_path)
    conn.row_factory = sqlite3.Row
    h_repo = PortfolioHoldingRepository(conn)
    h_repo.create("VNM", 500, 80.0, user_id="user_b")
    conn.commit()
    conn.close()
    store.upsert(WatchlistItem(user_id="user_b", symbol="VNM", threshold_pct=5.0))

    price_source = MockPriceSource({"FPT": 125.0, "VNM": 75.0})

    # 3. Kiểm tra user_a
    res_a = run_portfolio_watch_agent(
        user_id="user_a",
        intent="all",
        price_source=price_source,
        watchlist_store=store,
    )
    assert res_a.portfolio_summary is not None
    assert res_a.portfolio_summary.total_nav == 125_000_000.0
    assert res_a.portfolio_summary.total_cost == 100_000_000.0
    assert res_a.portfolio_summary.total_unrealized_pnl == 25_000_000.0
    assert "FPT" in res_a.formatted_markdown
    assert "VNM" not in res_a.formatted_markdown, "user_a không được thấy cổ phiếu của user_b!"
    assert "±3.0%" in res_a.formatted_markdown

    # 4. Kiểm tra user_b
    res_b = run_portfolio_watch_agent(
        user_id="user_b",
        intent="all",
        price_source=price_source,
        watchlist_store=store,
    )
    assert res_b.portfolio_summary is not None
    assert res_b.portfolio_summary.total_nav == 37_500_000.0
    assert "VNM" in res_b.formatted_markdown
    assert "FPT" not in res_b.formatted_markdown, "user_b không được thấy cổ phiếu của user_a!"
    assert "±5.0%" in res_b.formatted_markdown


# ==============================================================================
# 4. End-to-End Chat Graph Integration Tests (Golden v6 cases)
# ==============================================================================

def test_chat_graph_portfolio_01_end_to_end(test_db_path, monkeypatch):
    """portfolio_01: 'Danh mục đầu tư của tôi đang lãi hay lỗ như thế nào?' -> returns formatted P&L."""
    from backend.shared.settings import settings
    monkeypatch.setenv("SQLITE_PATH", test_db_path)
    monkeypatch.setattr(settings, "sqlite_path", test_db_path)

    conn = sqlite3.connect(test_db_path)
    conn.row_factory = sqlite3.Row
    h_repo = PortfolioHoldingRepository(conn)
    h_repo.create("HPG", 2000, 25.0, user_id="default")
    conn.commit()
    conn.close()

    price_source = MockPriceSource({"HPG": 28.0})
    store = SqliteWatchlistStore(test_db_path)

    result = run_chat_graph(
        question="Danh mục đầu tư của tôi đang lãi hay lỗ như thế nào?",
        price_source=price_source,
        news_source=DummyNewsSource(),  # type: ignore
        history_store=DummyHistoryStore(),  # type: ignore
        memory_store=DummyMemoryStore(),
        watchlist_store=store,
        user_id="default",
    )
    assert result.routing.route == "portfolio" or "portfolio_watch" in result.routing.agents_to_call
    assert "HPG" in result.answer
    assert "NAV" in result.answer or "Lãi/Lỗ" in result.answer
    assert "nên mua" not in result.answer.lower()
    assert "nên bán" not in result.answer.lower()


def test_chat_graph_portfolio_02_no_fake_tra_nav_ticker(test_db_path, monkeypatch):
    """portfolio_02: 'Kiểm tra hiệu suất P&L và tổng giá trị NAV của danh mục hiện tại' -> zero fake TRA/NAV lookups."""
    from backend.shared.settings import settings
    monkeypatch.setenv("SQLITE_PATH", test_db_path)
    monkeypatch.setattr(settings, "sqlite_path", test_db_path)

    price_source = MockPriceSource()
    store = SqliteWatchlistStore(test_db_path)

    result = run_chat_graph(
        question="Kiểm tra hiệu suất P&L và tổng giá trị NAV của danh mục hiện tại",
        price_source=price_source,
        news_source=DummyNewsSource(),  # type: ignore
        history_store=DummyHistoryStore(),  # type: ignore
        memory_store=DummyMemoryStore(),
        watchlist_store=store,
        user_id="default",
    )
    assert "TRA" not in (result.rewritten.symbols or [])
    assert "NAV" not in (result.rewritten.symbols or [])
    assert result.price is None
    assert "nên mua" not in result.answer.lower()
    assert "nên bán" not in result.answer.lower()


def test_chat_graph_watchlist_01_and_02_end_to_end(test_db_path, monkeypatch):
    """watchlist_01 and watchlist_02: returns watchlist and thresholds without fake XEM ticker."""
    from backend.shared.settings import settings
    monkeypatch.setenv("SQLITE_PATH", test_db_path)
    monkeypatch.setattr(settings, "sqlite_path", test_db_path)

    store = SqliteWatchlistStore(test_db_path)
    store.upsert(WatchlistItem(user_id="default", symbol="FPT", threshold_pct=3.0))
    store.upsert(WatchlistItem(user_id="default", symbol="MWG", threshold_pct=4.5))

    price_source = MockPriceSource()

    # watchlist_01
    res1 = run_chat_graph(
        question="Danh sách theo dõi watchlist của tôi hiện có những mã nào?",
        price_source=price_source,
        news_source=DummyNewsSource(),  # type: ignore
        history_store=DummyHistoryStore(),  # type: ignore
        memory_store=DummyMemoryStore(),
        watchlist_store=store,
        user_id="default",
    )
    assert "FPT" in res1.answer
    assert "MWG" in res1.answer
    assert "nên mua" not in res1.answer.lower()
    assert "nên bán" not in res1.answer.lower()

    # watchlist_02
    res2 = run_chat_graph(
        question="Xem các mã trong danh sách theo dõi kèm ngưỡng cảnh báo biến động",
        price_source=price_source,
        news_source=DummyNewsSource(),  # type: ignore
        history_store=DummyHistoryStore(),  # type: ignore
        memory_store=DummyMemoryStore(),
        watchlist_store=store,
        user_id="default",
    )
    assert "XEM" not in (res2.rewritten.symbols or [])
    assert "±3.0%" in res2.answer
    assert "±4.5%" in res2.answer
    assert "nên mua" not in res2.answer.lower()
    assert "nên bán" not in res2.answer.lower()
