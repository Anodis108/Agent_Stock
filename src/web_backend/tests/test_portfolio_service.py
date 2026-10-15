"""Unit & Integration tests for PortfolioService: P&L calculations, NAV, and Multi-tenant SQLite isolation."""

from __future__ import annotations

import sqlite3
import pytest

from common.domain.ports import PriceBar, PriceQuote
from web_backend.application.portfolio_service import (
    PortfolioItemSummary,
    PortfolioService,
    PortfolioSummary,
)
from web_backend.infra.database.connection import init_db
from web_backend.infra.database.repositories import (
    PortfolioHoldingRepository,
    UserSettingsRepository,
)


class MockPriceSource:
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


def test_portfolio_pnl_mathematical_precision(in_memory_db: sqlite3.Connection):
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

    service.add_holding("FPT", quantity=1000, avg_buy_price=100.0, user_id="user_a")
    service.add_holding("HPG", quantity=2000, avg_buy_price=30.0, user_id="user_a")
    service.add_holding("VNM", quantity=500, avg_buy_price=70.0, user_id="user_a")

    summary = service.get_portfolio_summary(user_id="user_a")

    # Chi phí vốn: 100M + 60M + 35M = 195,000,000 VND
    assert summary.total_cost == 195_000_000.0
    # Giá trị thị trường (NAV): 125M + 48M + 35M = 208,000,000 VND
    assert summary.total_nav == 208_000_000.0
    # Unrealized P&L: 208M - 195M = +13,000,000 VND
    assert summary.total_unrealized_pnl == 13_000_000.0
    # Tỷ suất sinh lời: (13M / 195M) * 100 = 6.67%
    assert round(summary.total_pnl_pct, 2) == 6.67
    assert summary.count == 3


def test_portfolio_multi_tenant_isolation(in_memory_db: sqlite3.Connection):
    """Đảm bảo cô lập dữ liệu tuyệt đối giữa các user_id."""
    holdings_repo = PortfolioHoldingRepository(in_memory_db)
    user_settings_repo = UserSettingsRepository(in_memory_db)
    price_source = MockPriceSource({"FPT": 120.0, "HPG": 28.0})

    service = PortfolioService(
        holdings_repo=holdings_repo,
        user_settings_repo=user_settings_repo,
        price_source=price_source,
    )

    # User A nắm giữ FPT
    service.add_holding("FPT", quantity=100, avg_buy_price=100.0, user_id="user_a")
    # User B nắm giữ HPG
    service.add_holding("HPG", quantity=500, avg_buy_price=25.0, user_id="user_b")

    summary_a = service.get_portfolio_summary("user_a")
    summary_b = service.get_portfolio_summary("user_b")
    summary_default = service.get_portfolio_summary("default")

    assert summary_a.count == 1
    assert summary_a.items[0].symbol == "FPT"
    assert summary_b.count == 1
    assert summary_b.items[0].symbol == "HPG"
    assert summary_default.count == 0


def test_portfolio_missing_price_fallback(in_memory_db: sqlite3.Connection):
    """Khi mất kết nối nguồn giá hoặc mã không tồn tại, thị giá fallback bằng giá vốn."""
    holdings_repo = PortfolioHoldingRepository(in_memory_db)
    user_settings_repo = UserSettingsRepository(in_memory_db)
    price_source = MockPriceSource({"FPT": None})  # Không có giá FPT

    service = PortfolioService(
        holdings_repo=holdings_repo,
        user_settings_repo=user_settings_repo,
        price_source=price_source,
    )

    service.add_holding("FPT", quantity=100, avg_buy_price=100.0, user_id="default")
    summary = service.get_portfolio_summary("default")

    item = summary.items[0]
    assert item.price_error is True
    assert item.cost_basis == 10_000_000.0
    assert item.market_value == 10_000_000.0
    assert item.unrealized_pnl == 0.0
