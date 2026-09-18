"""Phase 5 — Backend input lỗi → 4xx rõ (câu rỗng, symbol invalid, ngưỡng âm)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from backend.main import app, store
from backend.store import WatchlistItem


def setup_function():
    store.clear()
    store.upsert_watchlist(WatchlistItem(symbol="FPT", threshold_pct=3.0))


def test_chat_empty_question_400():
    client = TestClient(app)
    for q in ("", "   "):
        resp = client.post("/chat", json={"question": q})
        assert resp.status_code == 400
        assert "rỗng" in resp.json()["detail"]


def test_symbol_invalid_or_empty_400():
    client = TestClient(app)
    # rỗng
    empty = client.post("/watchlist", json={"symbol": "  ", "threshold_pct": 3.0})
    assert empty.status_code == 400
    assert "rỗng" in empty.json()["detail"]

    # invalid (không đúng 3 chữ)
    for sym in ("A", "ABCD", "F1", "12", "FPT!"):
        resp = client.post("/scan", json={"symbol": sym})
        assert resp.status_code == 400, sym
        detail = resp.json()["detail"]
        assert "hợp lệ" in detail or "rỗng" in detail


def test_negative_threshold_400():
    client = TestClient(app)
    # watchlist create
    w = client.post("/watchlist", json={"symbol": "VNM", "threshold_pct": -1.0})
    assert w.status_code == 400
    assert "âm" in w.json()["detail"]

    # watchlist patch
    p = client.patch("/watchlist/FPT", json={"threshold_pct": -0.5})
    assert p.status_code == 400
    assert "âm" in p.json()["detail"]

    # scan
    s = client.post("/scan", json={"symbol": "FPT", "threshold_pct": -2.0})
    assert s.status_code == 400
    assert "âm" in s.json()["detail"]


def test_zero_threshold_still_400():
    client = TestClient(app)
    resp = client.post("/watchlist", json={"symbol": "VNM", "threshold_pct": 0})
    assert resp.status_code == 400
    assert "detail" in resp.json()
