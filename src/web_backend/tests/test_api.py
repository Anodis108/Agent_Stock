"""Integration tests for Web Backend REST API endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from web_backend.infra.database.connection import get_connection
from web_backend.infra.database.repositories import (
    PortfolioHoldingRepository,
    SessionRepository,
    WatchlistRepository,
)


def test_health_endpoint(client: TestClient):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["service"] == "web_backend"


def test_watchlist_crud_api(client: TestClient):
    # 1. Add to watchlist
    add_resp = client.post("/watchlist", json={"symbol": "FPT", "threshold_pct": 3.5})
    assert add_resp.status_code == 200
    assert add_resp.json()["symbol"] == "FPT"
    assert add_resp.json()["threshold_pct"] == 3.5

    # 2. Get watchlist
    get_resp = client.get("/watchlist")
    assert get_resp.status_code == 200
    items = get_resp.json()["items"]
    assert any(it["symbol"] == "FPT" for it in items)

    # 3. Patch / Update
    patch_resp = client.patch("/watchlist/FPT", json={"threshold_pct": 5.0})
    assert patch_resp.status_code == 200
    assert patch_resp.json()["threshold_pct"] == 5.0

    # 4. Delete
    del_resp = client.delete("/watchlist/FPT")
    assert del_resp.status_code == 200
    assert del_resp.json()["status"] == "success"


def test_portfolio_holdings_api(client: TestClient):
    # 1. Add holding
    add_resp = client.post(
        "/api/portfolio/holdings",
        json={"symbol": "HPG", "quantity": 1000, "avg_buy_price": 28.5},
        headers={"X-User-ID": "user_a"},
    )
    assert add_resp.status_code == 200
    holding_id = add_resp.json()["id"]

    # 2. Get portfolio holdings
    list_resp = client.get("/api/portfolio/holdings", headers={"X-User-ID": "user_a"})
    assert list_resp.status_code == 200
    data = list_resp.json()
    assert data["count"] >= 1
    assert any(h["symbol"] == "HPG" for h in data["items"])

    # 3. Delete holding
    del_resp = client.delete(f"/api/portfolio/holdings/{holding_id}", headers={"X-User-ID": "user_a"})
    assert del_resp.status_code == 200
    assert del_resp.json()["status"] == "success"


def test_sessions_api(client: TestClient):
    # 1. Create session
    create_resp = client.post("/api/v1/sessions", json={"title": "Hội thoại thử nghiệm"})
    assert create_resp.status_code == 201
    sess_id = create_resp.json()["id"]

    # 2. List sessions
    list_resp = client.get("/api/v1/sessions")
    assert list_resp.status_code == 200
    assert any(s["id"] == sess_id for s in list_resp.json()["items"])

    # 3. Get session details
    detail_resp = client.get(f"/api/v1/sessions/{sess_id}")
    assert detail_resp.status_code == 200
    assert detail_resp.json()["session"]["id"] == sess_id

    # 4. Delete session
    del_resp = client.delete(f"/api/v1/sessions/{sess_id}")
    assert del_resp.status_code == 200
    assert del_resp.json()["status"] == "success"


def test_scan_api(client: TestClient):
    resp = client.post("/scan", json={"symbols": ["FPT", "VNM"]})
    assert resp.status_code == 200
    assert "alerts" in resp.json() or "results" in resp.json()


def test_market_sessions_api(client: TestClient):
    resp = client.get("/api/market/sessions")
    assert resp.status_code == 200
    sessions = resp.json()
    assert isinstance(sessions, list)
    assert len(sessions) > 0
    assert any(s["session_type"] == "ATO" for s in sessions)
