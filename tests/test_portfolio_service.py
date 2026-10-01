"""Unit & Integration tests for PortfolioService: P&L calculations, NAV, and Multi-tenant SQLite isolation."""

from __future__ import annotations

import sqlite3
import pytest

from backend.database.connection import init_db
from backend.database.repositories import (
    PortfolioHoldingRepository,
    UserSettingsRepository,
)
from backend.domain.ports import PriceBar, PriceQuote, PriceSourcePort
from backend.services.portfolio_service import (
    PortfolioItemSummary,
    PortfolioService,
    PortfolioSummary,
)


class MockPriceSource(PriceSourcePort):
    def __init__(self, quotes: dict[str, float | None] | None = None) -> None:
        self.quotes = quotes or {}

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


@pytest.fixture
def in_memory_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_db(conn)
    yield conn
    conn.close()


def test_portfolio_pnl_mathematical_precision(in_memory_db):
    """Kiểm tra độ chính xác công thức toán học:
    - Unrealized P&L = (current_price - avg_buy_price) * quantity
    - Total NAV = sum(current_price * quantity)
    - P&L % = (Unrealized P&L / Cost Basis) * 100
    """
    holdings_repo = PortfolioHoldingRepository(in_memory_db)
    user_settings_repo = UserSettingsRepository(in_memory_db)

    # Giả lập giá thị trường:
    # FPT: giá vốn 100.0 (100k), thị giá 125.0 (125k), SL: 1,000 CP -> Lãi 25k * 1,000 = 25,000,000 VND (+25%)
    # HPG: giá vốn 30.0 (30k), thị giá 24.0 (24k), SL: 2,000 CP -> Lỗ -6k * 2,000 = -12,000,000 VND (-20%)
    # VNM: giá vốn 70.0 (70k), thị giá 70.0 (70k), SL: 500 CP -> Hòa vốn 0 VND (0%)
    price_source = MockPriceSource(
        {
            "FPT": 125.0,
            "HPG": 24.0,
            "VNM": 70.0,
        }
    )

    service = PortfolioService(
        holdings_repo=holdings_repo,
        user_settings_repo=user_settings_repo,
        price_source=price_source,
    )

    user_id = "test_user_pnl"
    service.add_holding("FPT", quantity=1000, avg_buy_price=100.0, user_id=user_id)
    service.add_holding("HPG", quantity=2000, avg_buy_price=30.0, user_id=user_id)
    service.add_holding("VNM", quantity=500, avg_buy_price=70.0, user_id=user_id)

    summary = service.get_portfolio_summary(user_id=user_id)

    assert summary.count == 3
    # Cost Basis từng mã:
    # FPT: 100,000,000 VND
    # HPG: 60,000,000 VND
    # VNM: 35,000,000 VND
    # Tổng Cost: 195,000,000 VND
    assert summary.total_cost == 195_000_000.0

    # Market Value (NAV):
    # FPT: 1,000 * 125,000 = 125,000,000 VND
    # HPG: 2,000 * 24,000 = 48,000,000 VND
    # VNM: 500 * 70,000 = 35,000,000 VND
    # Tổng NAV = sum(current_price * quantity) = 208,000,000 VND
    assert summary.total_nav == 208_000_000.0

    # Unrealized P&L:
    # FPT: +25,000,000 VND (+25%)
    # HPG: -12,000,000 VND (-20%)
    # VNM: 0 VND (0%)
    # Tổng Lãi/Lỗ: 25M - 12M = +13,000,000 VND
    assert summary.total_unrealized_pnl == 13_000_000.0

    # Tỷ suất % P&L tổng thể = (13M / 195M) * 100 = 6.6666...%
    expected_pct = (13_000_000.0 / 195_000_000.0) * 100.0
    assert abs(summary.total_pnl_pct - expected_pct) < 0.01

    # Kiểm tra chi tiết từng holding
    items_by_sym = {item.symbol: item for item in summary.items}
    fpt = items_by_sym["FPT"]
    assert fpt.unrealized_pnl == 25_000_000.0
    assert fpt.pnl_pct == 25.0
    assert fpt.price_error is False

    hpg = items_by_sym["HPG"]
    assert hpg.unrealized_pnl == -12_000_000.0
    assert hpg.pnl_pct == -20.0

    vnm = items_by_sym["VNM"]
    assert vnm.unrealized_pnl == 0.0
    assert vnm.pnl_pct == 0.0


def test_portfolio_multi_tenant_isolation(in_memory_db):
    """Kiểm tra cô lập dữ liệu tuyệt đối giữa các user_id:
    - User A chỉ thấy vị thế của User A.
    - User B chỉ thấy vị thế của User B.
    - User A không thể xóa vị thế của User B.
    """
    holdings_repo = PortfolioHoldingRepository(in_memory_db)
    user_settings_repo = UserSettingsRepository(in_memory_db)
    price_source = MockPriceSource({"SSI": 35.0, "TCB": 25.0})

    service = PortfolioService(
        holdings_repo=holdings_repo,
        user_settings_repo=user_settings_repo,
        price_source=price_source,
    )

    user_a = "investor_alice"
    user_b = "investor_bob"

    # Alice mua SSI
    h_alice = service.add_holding("SSI", quantity=1000, avg_buy_price=30.0, user_id=user_a)
    # Bob mua TCB
    h_bob = service.add_holding("TCB", quantity=2000, avg_buy_price=22.0, user_id=user_b)

    # 1. Kiểm tra danh mục Alice
    sum_a = service.get_portfolio_summary(user_id=user_a)
    assert sum_a.count == 1
    assert sum_a.items[0].symbol == "SSI"
    assert sum_a.user_id == user_a

    # 2. Kiểm tra danh mục Bob
    sum_b = service.get_portfolio_summary(user_id=user_b)
    assert sum_b.count == 1
    assert sum_b.items[0].symbol == "TCB"
    assert sum_b.user_id == user_b

    # 3. Alice cố tình xóa vị thế của Bob -> Từ chối (False)
    del_cross_attempt = service.delete_holding(holding_id=h_bob.id, user_id=user_a)
    assert del_cross_attempt is False

    # Vị thế của Bob vẫn còn nguyên vẹn
    sum_b_after = service.get_portfolio_summary(user_id=user_b)
    assert sum_b_after.count == 1
    assert sum_b_after.items[0].id == h_bob.id

    # 4. Bob xóa vị thế của chính mình -> Thành công (True)
    del_bob_ok = service.delete_holding(holding_id=h_bob.id, user_id=user_b)
    assert del_bob_ok is True
    assert service.get_portfolio_summary(user_id=user_b).count == 0


def test_portfolio_empty_state_and_graceful_fallback(in_memory_db):
    """Kiểm tra:
    - Danh mục rỗng (Empty State) trả về NAV = 0, P&L = 0
    - Fallback an toàn khi PriceSource gặp lỗi
    """
    holdings_repo = PortfolioHoldingRepository(in_memory_db)
    user_settings_repo = UserSettingsRepository(in_memory_db)
    price_source = MockPriceSource({"ERROR_SYM": None})

    service = PortfolioService(
        holdings_repo=holdings_repo,
        user_settings_repo=user_settings_repo,
        price_source=price_source,
    )

    # 1. User rỗng
    empty_summary = service.get_portfolio_summary("empty_user")
    assert empty_summary.total_nav == 0.0
    assert empty_summary.total_cost == 0.0
    assert empty_summary.total_unrealized_pnl == 0.0
    assert empty_summary.total_pnl_pct == 0.0
    assert empty_summary.items == []
    assert empty_summary.count == 0

    # 2. Mã lỗi giá -> fallback giữ nguyên giá vốn, price_error = True
    service.add_holding("ERROR_SYM", quantity=100, avg_buy_price=50.0, user_id="user_err")
    err_summary = service.get_portfolio_summary("user_err")
    assert err_summary.count == 1
    item = err_summary.items[0]
    assert item.price_error is True
    assert item.current_price is None
    assert item.market_value == item.cost_basis  # Fallback về cost_basis
    assert item.unrealized_pnl == 0.0
    assert item.pnl_pct == 0.0
