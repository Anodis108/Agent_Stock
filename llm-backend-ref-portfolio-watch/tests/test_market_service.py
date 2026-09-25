"""Unit tests for MarketService (backend/services/market_service.py)."""

from __future__ import annotations

import sqlite3
from unittest.mock import MagicMock

import pytest

from backend.database.connection import get_connection
from backend.database.repositories import MarketHistoryRepository
from backend.domain.ports import PriceBar
from backend.services.market_service import (
    DEFAULT_BASE_PRICES,
    DEFAULT_MARKET_SYMBOLS,
    MarketService,
    get_market_service,
)


@pytest.fixture
def mem_db():
    conn = get_connection(":memory:")
    yield conn
    conn.close()


def test_default_market_symbols_count_and_items():
    """Verify default market symbols contains exactly the 10 required tickers."""
    expected = ["FPT", "VNM", "HPG", "VHM", "VIC", "TCB", "MBB", "SSI", "MWG", "VCB"]
    assert DEFAULT_MARKET_SYMBOLS == expected
    assert len(DEFAULT_MARKET_SYMBOLS) == 10
    for sym in expected:
        assert sym in DEFAULT_BASE_PRICES


def test_sync_symbol_history_with_mock_pricesource(mem_db: sqlite3.Connection):
    """Verify synchronization computes change_pct and caches bars into SQLite."""
    mock_source = MagicMock()
    mock_source.fetch_history.return_value = [
        PriceBar(date="2026-09-01", close=100.0, open_price=98.0, high=101.0, low=97.0, volume=1000000.0),
        PriceBar(date="2026-09-02", close=105.0, open_price=101.0, high=106.0, low=100.0, volume=1200000.0),
        PriceBar(date="2026-09-03", close=102.9, open_price=104.0, high=105.0, low=102.0, volume=900000.0),
    ]

    service = MarketService(conn=mem_db, price_source=mock_source)
    records = service.sync_symbol_history("FPT", days=5)

    assert len(records) == 3
    # First day change_pct = (100 - 98) / 98 * 100 = 2.04%
    assert records[0].change_pct == 2.04
    # Second day change_pct = (105 - 100) / 100 * 100 = 5.0%
    assert records[1].change_pct == 5.0
    # Third day change_pct = (102.9 - 105) / 105 * 100 = -2.0%
    assert records[2].change_pct == -2.0

    # Verify data in SQLite table market_history_10d
    repo = MarketHistoryRepository(mem_db)
    cached = repo.get_history("FPT", limit=10, ascending=True)
    assert len(cached) == 3
    assert cached[0].trade_date == "2026-09-01"
    assert cached[1].close == 105.0
    assert cached[2].volume == 900000


def test_sync_symbol_history_fallback_on_empty(mem_db: sqlite3.Connection):
    """Verify fallback synthesizer creates 10 valid bars when source returns empty."""
    mock_source = MagicMock()
    mock_source.fetch_history.return_value = []

    service = MarketService(conn=mem_db, price_source=mock_source)
    records = service.sync_symbol_history("HPG", days=10, fallback_on_empty=True)

    assert len(records) == 10
    assert all(r.symbol == "HPG" for r in records)
    assert all(r.close > 0 for r in records)
    assert all(r.trade_date != "" for r in records)
    assert all(r.volume is not None and r.volume > 0 for r in records)

    # Verify cached in DB
    repo = MarketHistoryRepository(mem_db)
    cached = repo.get_history("HPG", limit=10)
    assert len(cached) == 10


def test_sync_all_default_symbols(mem_db: sqlite3.Connection):
    """Verify sync_all_default_symbols synchronizes all 10 tickers."""
    mock_source = MagicMock()
    # Let it fallback to synthesis
    mock_source.fetch_history.return_value = []

    service = MarketService(conn=mem_db, price_source=mock_source)
    results = service.sync_all_default_symbols(days=10)

    assert len(results) == 10
    for sym in DEFAULT_MARKET_SYMBOLS:
        assert sym in results
        assert len(results[sym]) == 10

    # Check distinct symbols in SQLite
    repo = MarketHistoryRepository(mem_db)
    tracked = repo.get_tracked_symbols()
    assert sorted(tracked) == sorted(DEFAULT_MARKET_SYMBOLS)


def test_get_symbol_history_with_auto_sync(mem_db: sqlite3.Connection):
    """Verify get_symbol_history triggers auto-sync when DB is empty."""
    mock_source = MagicMock()
    mock_source.fetch_history.return_value = []

    service = MarketService(conn=mem_db, price_source=mock_source)
    # DB initially empty
    bars = service.get_symbol_history("VNM", limit=10, auto_sync=True)
    assert len(bars) == 10
    assert bars[0].symbol == "VNM"


def test_get_matrix_10d_computation(mem_db: sqlite3.Connection):
    """Verify matrix format, sparkline series, volume sums, and session details."""
    mock_source = MagicMock()
    mock_source.fetch_history.return_value = [
        PriceBar(date=f"2026-09-{i:02d}", close=100.0 + i, open_price=99.0 + i, high=101.0 + i, low=98.0 + i, volume=1000.0)
        for i in range(1, 11)
    ]

    service = MarketService(conn=mem_db, price_source=mock_source)
    matrix = service.get_matrix_10d(symbols=["FPT", "SSI"], days=10, auto_sync=True)

    assert len(matrix) == 2
    fpt_entry = next(item for item in matrix if item["symbol"] == "FPT")

    assert fpt_entry["current_price"] == 110.0
    assert len(fpt_entry["sparkline"]) == 10
    assert fpt_entry["sparkline"][0] == 101.0
    assert fpt_entry["sparkline"][-1] == 110.0
    assert fpt_entry["total_volume"] == 10000
    assert len(fpt_entry["sessions"]) == 10
    assert fpt_entry["sessions"][-1]["date"] == "2026-09-10"
    assert fpt_entry["sessions"][-1]["close"] == 110.0


def test_factory_helpers(mem_db: sqlite3.Connection):
    """Verify get_market_service factory."""
    service = get_market_service(conn=mem_db)
    assert isinstance(service, MarketService)
    assert service.conn == mem_db
