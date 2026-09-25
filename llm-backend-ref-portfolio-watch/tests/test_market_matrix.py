"""Unit and integration tests for Market Watch Matrix (10D) REST API.

Tests:
- GET /api/v1/market/matrix-10d (default 10 tickers x 10 days)
- GET /api/market/matrix-10d (alias route)
- GET /market/matrix-10d (direct route)
- Query parameters: custom symbols, custom days
- Data accuracy: sparklines, price changes, session OHLCV
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.backend.main import app as product_app
from backend.database.connection import get_connection
from backend.services.market_service import DEFAULT_MARKET_SYMBOLS


@pytest.fixture
def client(tmp_path, monkeypatch):
    """TestClient wired to an isolated temporary SQLite database."""
    temp_db = tmp_path / "test_market_matrix.db"
    monkeypatch.setenv("SQLITE_PATH", str(temp_db))
    conn = get_connection(temp_db)
    conn.close()
    return TestClient(product_app)


def test_get_matrix_10d_default_symbols(client: TestClient):
    """GET /api/v1/market/matrix-10d returns 10 default tickers x 10 days."""
    resp = client.get("/api/v1/market/matrix-10d")
    assert resp.status_code == 200
    data = resp.json()

    assert "items" in data
    assert "count" in data
    assert "updated_at" in data
    assert data["count"] == 10
    assert len(data["items"]) == 10

    returned_symbols = [item["symbol"] for item in data["items"]]
    assert returned_symbols == DEFAULT_MARKET_SYMBOLS

    for item in data["items"]:
        assert item["symbol"] in DEFAULT_MARKET_SYMBOLS
        assert item["current_price"] > 0
        assert isinstance(item["change_pct"], (int, float))
        assert item["total_volume"] >= 0

        # Sparkline must have 10 data points
        assert len(item["sparkline"]) == 10
        assert all(isinstance(p, (int, float)) and p > 0 for p in item["sparkline"])

        # Sessions must have 10 entries ordered chronologically
        assert len(item["sessions"]) == 10
        dates = [s["date"] for s in item["sessions"]]
        assert dates == sorted(dates)

        last_session = item["sessions"][-1]
        assert last_session["close"] == item["current_price"]
        assert last_session["change_pct"] == item["change_pct"]
        assert "open" in last_session
        assert "high" in last_session
        assert "low" in last_session
        assert "volume" in last_session


def test_get_matrix_10d_custom_symbols(client: TestClient):
    """GET /api/v1/market/matrix-10d with custom comma-separated tickers."""
    resp = client.get("/api/v1/market/matrix-10d?symbols=FPT,HPG,VNM")
    assert resp.status_code == 200
    data = resp.json()

    assert data["count"] == 3
    symbols = [item["symbol"] for item in data["items"]]
    assert symbols == ["FPT", "HPG", "VNM"]


def test_get_matrix_10d_custom_days(client: TestClient):
    """GET /api/v1/market/matrix-10d with custom days=5."""
    resp = client.get("/api/v1/market/matrix-10d?symbols=TCB&days=5")
    assert resp.status_code == 200
    data = resp.json()

    assert data["count"] == 1
    tcb_item = data["items"][0]
    assert tcb_item["symbol"] == "TCB"
    assert len(tcb_item["sessions"]) == 5
    assert len(tcb_item["sparkline"]) == 5


def test_get_matrix_10d_alias_routes(client: TestClient):
    """Verify alias routes /api/market/matrix-10d and /market/matrix-10d."""
    # Test /api/market/matrix-10d
    res1 = client.get("/api/market/matrix-10d?symbols=SSI")
    assert res1.status_code == 200
    assert res1.json()["items"][0]["symbol"] == "SSI"

    # Test /market/matrix-10d
    res2 = client.get("/market/matrix-10d?symbols=SSI")
    assert res2.status_code == 200
    assert res2.json()["items"][0]["symbol"] == "SSI"
