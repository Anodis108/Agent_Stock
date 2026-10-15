"""Unit and integration tests for MarketService and Market API in Web Backend."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from web_backend.application.market_service import (
    DEFAULT_MARKET_SYMBOLS,
    MarketInput,
    MarketService,
)


def test_default_market_symbols():
    expected = ["FPT", "VNM", "HPG", "VHM", "VIC", "TCB", "MBB", "SSI", "MWG", "VCB"]
    assert DEFAULT_MARKET_SYMBOLS == expected
    assert len(DEFAULT_MARKET_SYMBOLS) == 10


def test_market_service_sessions():
    service = MarketService()
    sessions = service.get_trading_sessions()
    assert isinstance(sessions, list)
    assert len(sessions) >= 3
    types = [s.session_type for s in sessions]
    assert "ATO" in types
    assert "ATC" in types


def test_market_service_matrix_fallback():
    service = MarketService()
    matrix = service.get_matrix_data(["FPT", "HPG"])
    assert len(matrix) == 2
    for item in matrix:
        assert item["symbol"] in ("FPT", "HPG")
        assert "sparkline" in item
        assert len(item["sparkline"]) == 10
        assert "current_price" in item


def test_market_service_process():
    service = MarketService()
    out = service.process(MarketInput(action="sessions"))
    assert out.sessions is not None
    assert len(out.sessions) >= 3

    out_matrix = service.process(MarketInput(action="matrix", symbols=["FPT"]))
    assert out_matrix.matrix is not None
    assert len(out_matrix.matrix) == 1
