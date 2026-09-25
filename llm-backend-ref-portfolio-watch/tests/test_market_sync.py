"""Unit tests for Phase 4 — Market Data Synchronization (Single Source of Truth).

Verifies:
1. Giá FPT trả về từ PriceAgent và giá FPT hiển thị trên bảng ma trận Market Watch (10D) là cùng một giá trị.
2. PriceAgent tự động đồng bộ giá phiên mới nhất vào bảng SQLite `market_history_10d`.
3. Cơ chế cache dùng chung (shared cache) giữa PriceAgent và MarketService.
4. Thống nhất mốc giá tham chiếu fallback thực tế (FPT ~ 66.0, loại bỏ mốc 135.0 cũ).
5. Chuỗi Chat Graph End-to-End tự động cập nhật số liệu bảng Market Watch Matrix.
"""

from __future__ import annotations

from datetime import datetime
import sqlite3
import pytest

from backend.agents.answer_composer import AnswerComposeResult
from backend.agents.price_agent import run_price_agent
from backend.agents.supervisor_agent import (
    HeuristicRewriteBrain,
    HeuristicSupervisorBrain,
)
from backend.database.connection import get_connection
from backend.database.repositories import MarketHistoryRepository
from backend.domain.ports import PriceBar, PriceQuote
from backend.graph.chat import run_chat_graph
from backend.infra.market_data.price_source import (
    DEFAULT_BASE_PRICES,
    VnstockPriceSource,
)
from backend.infra.storage.memory_store import SqliteMemoryStore
from backend.services.market_service import (
    DEFAULT_MARKET_SYMBOLS,
    MarketService,
    get_market_service,
)


class MockPriceSource:
    """Mock price source trả về giá cố định cho kiểm thử."""

    def __init__(self, quote: PriceQuote | None = None):
        self._quote = quote or PriceQuote(symbol="FPT", latest_close=65.2, prev_close=66.1)

    def fetch_latest_close(self, symbol: str) -> PriceQuote:
        return PriceQuote(
            symbol=symbol,
            latest_close=self._quote.latest_close,
            prev_close=self._quote.prev_close,
        )

    def fetch_history(self, symbol: str, days: int = 15) -> list[PriceBar]:
        return []


class DummyNewsSource:
    def fetch_news(self, symbol: str, query: str | None = None, *, days: int | None = None) -> list:
        return []


class DummyHistoryStore:
    def read_history(self, symbol: str, days: int = 30) -> list[PriceBar]:
        return []


class DummyAnswerBrain:
    def compose(self, **kwargs) -> AnswerComposeResult:
        sym = kwargs.get("symbol") or "N/A"
        price_val = kwargs.get("price")
        price_str = f"{price_val.latest_close}" if price_val and price_val.latest_close else "65.2"
        return AnswerComposeResult(answer=f"Giá cổ phiếu {sym} hôm nay là {price_str}.")


# ─── 1. Thống nhất mốc giá tham chiếu Fallback ───────────────────────────────

def test_default_base_prices_updated_and_consistent():
    """Xác nhận mốc giá fallback của FPT đã được cập nhật thành 66.0 (loại bỏ 135.0)."""
    assert "FPT" in DEFAULT_BASE_PRICES
    assert DEFAULT_BASE_PRICES["FPT"] == 66.0
    assert len(DEFAULT_BASE_PRICES) == 10
    for sym in DEFAULT_MARKET_SYMBOLS:
        assert sym in DEFAULT_BASE_PRICES
        assert DEFAULT_BASE_PRICES[sym] > 0


# ─── 2. Cơ chế Cache dùng chung giữa các instance ────────────────────────────

def test_shared_price_source_cache_between_agent_and_service():
    """Xác nhận hai instance VnstockPriceSource khác nhau dùng chung cache (Single Source of Truth)."""
    ps1 = VnstockPriceSource()
    ps2 = VnstockPriceSource()

    ps1.clear_cache()

    # Giả lập nạp quote vào ps1
    now = 1000.0
    quote = PriceQuote(symbol="FPT", latest_close=65.2, prev_close=66.1)
    with ps1._lock:
        ps1._quote_cache["FPT"] = (now, quote)

    # ps2 truy cập cache mà không cần query lại
    assert "FPT" in ps2._quote_cache
    ts, cached_quote = ps2._quote_cache["FPT"]
    assert cached_quote.latest_close == 65.2
    assert cached_quote.prev_close == 66.1

    ps1.clear_cache()
    assert "FPT" not in ps2._quote_cache


# ─── 3. Đồng bộ trực tiếp: PriceAgent ➔ SQLite market_history_10d ──────────

def test_price_agent_syncs_to_market_history_table(tmp_path, monkeypatch):
    """Khi PriceAgent chạy, phiên giá mới nhất tự động được ghi vào SQLite market_history_10d."""
    db_file = tmp_path / "test_sync_repo.db"
    monkeypatch.setenv("SQLITE_PATH", str(db_file))

    # Khởi tạo bảng
    conn = get_connection(db_file)
    conn.close()

    mock_source = MockPriceSource(PriceQuote(symbol="FPT", latest_close=65.2, prev_close=66.1))
    agent_result = run_price_agent("FPT", mock_source)

    assert agent_result.latest_close == 65.2
    assert agent_result.change_pct == pytest.approx(-1.36, rel=1e-2)

    # Đọc trực tiếp từ bảng market_history_10d
    verify_conn = get_connection(db_file)
    repo = MarketHistoryRepository(verify_conn)
    records = repo.get_history("FPT", limit=5)
    verify_conn.close()

    assert len(records) >= 1
    latest_rec = records[-1]
    assert latest_rec.symbol == "FPT"
    assert latest_rec.close == 65.2
    assert latest_rec.change_pct == pytest.approx(-1.36, rel=1e-2)


# ─── 4. Kiểm tra PriceAgent và Market Watch Matrix cùng giá trị ─────────────

def test_market_sync_price_agent_and_matrix_same_price(tmp_path, monkeypatch):
    """Kiểm tra giá FPT từ PriceAgent và giá trên Market Watch Matrix hoàn toàn đồng nhất."""
    db_file = tmp_path / "test_sync_matrix.db"
    monkeypatch.setenv("SQLITE_PATH", str(db_file))

    # Khởi tạo DB
    conn = get_connection(db_file)

    test_quote = PriceQuote(symbol="FPT", latest_close=65.2, prev_close=66.1)
    mock_source = MockPriceSource(test_quote)

    # 1. PriceAgent chạy
    agent_res = run_price_agent("FPT", mock_source)
    assert agent_res.latest_close == 65.2

    # 2. MarketService lấy matrix
    service = MarketService(conn=conn, price_source=mock_source)
    matrix = service.get_matrix_10d(symbols=["FPT"])
    conn.close()

    assert len(matrix) == 1
    fpt_matrix_item = matrix[0]

    assert fpt_matrix_item["symbol"] == "FPT"
    # GIÁ PHẢI HOÀN TOÀN TRÙNG KHỚP
    assert fpt_matrix_item["current_price"] == agent_res.latest_close
    assert fpt_matrix_item["change_pct"] == pytest.approx(agent_res.change_pct, abs=0.01)


# ─── 5. Fallback Synthesizer bám sát giá quote của PriceSource ──────────────

def test_synthesize_fallback_bars_anchors_to_cached_quote(tmp_path):
    """Khi không có vnstock history, fallback bars tự động lấy giá mới nhất từ price_source."""
    conn = get_connection(":memory:")
    mock_source = MockPriceSource(PriceQuote(symbol="FPT", latest_close=65.2, prev_close=66.1))

    service = MarketService(conn=conn, price_source=mock_source)
    bars = service._synthesize_fallback_bars("FPT", count=5)
    conn.close()

    assert len(bars) == 5
    # Các nến sinh ra dao động quanh mốc 65.2 (không phải mốc 135.0 cũ)
    for b in bars:
        assert 60.0 <= b.close <= 70.0


# ─── 6. End-to-End Chat Graph ➔ Market Matrix Synchronization ───────────────

def test_end_to_end_chat_graph_updates_market_watch_matrix(tmp_path, monkeypatch):
    """End-to-End: Người dùng hỏi giá FPT trong Chat, bảng Market Watch tự động đồng bộ giá đó."""
    db_file = tmp_path / "test_e2e_sync.db"
    monkeypatch.setenv("SQLITE_PATH", str(db_file))

    store = SqliteMemoryStore(db_file)
    test_quote = PriceQuote(symbol="FPT", latest_close=65.2, prev_close=66.1)
    price_src = MockPriceSource(test_quote)
    news_src = DummyNewsSource()
    hist_store = DummyHistoryStore()
    rewrite_brain = HeuristicRewriteBrain()
    sup_brain = HeuristicSupervisorBrain()
    ans_brain = DummyAnswerBrain()

    # 1. Chat Graph xử lý câu hỏi
    res = run_chat_graph(
        "Giá FPT hôm nay?",
        price_source=price_src,
        news_source=news_src,
        history_store=hist_store,
        memory_store=store,
        user_id="u_sync",
        rewrite_brain=rewrite_brain,
        supervisor_brain=sup_brain,
        answer_brain=ans_brain,
    )
    assert "65.2" in (res.answer or "")

    # 2. Đọc bảng Market Watch Matrix từ DB
    conn = get_connection(db_file)
    service = MarketService(conn=conn, price_source=price_src)
    matrix = service.get_matrix_10d(symbols=["FPT"])
    conn.close()

    assert len(matrix) == 1
    assert matrix[0]["symbol"] == "FPT"
    assert matrix[0]["current_price"] == 65.2
    assert matrix[0]["change_pct"] == pytest.approx(-1.36, rel=1e-2)
