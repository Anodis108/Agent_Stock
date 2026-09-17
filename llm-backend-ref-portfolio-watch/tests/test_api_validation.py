"""Phase 5 — API validate input → 4xx rõ ràng."""

from __future__ import annotations

from fastapi.testclient import TestClient

from src.portfolio_watch.api.deps import AppDeps, set_app_deps
from src.portfolio_watch.domain.entities import WatchlistItem
from src.portfolio_watch.domain.ports import PriceQuote
from src.portfolio_watch.main import app
from tests.fakes import (
    FakeMemoryStore,
    FakeNewsSource,
    FakeNotifier,
    FakePriceHistoryStore,
    FakePriceSource,
    FakeWatchlistStore,
)


def _client() -> TestClient:
    set_app_deps(
        AppDeps(
            price_source=FakePriceSource(
                PriceQuote("FPT", latest_close=100.0, prev_close=100.0)
            ),
            news_source=FakeNewsSource([[]]),
            history_store=FakePriceHistoryStore([]),
            memory_store=FakeMemoryStore(),
            notifier=FakeNotifier(),
            watchlist_store=FakeWatchlistStore(
                [WatchlistItem(symbol="FPT", threshold_pct=3.0)]
            ),
        )
    )
    return TestClient(app)


def teardown_function():
    set_app_deps(None)


def test_scan_empty_or_whitespace_symbol_400():
    client = _client()
    for sym in ("", "   "):
        resp = client.post("/scan", json={"symbol": sym})
        assert resp.status_code == 400
        assert "rỗng" in resp.json()["detail"]


def test_scan_invalid_symbol_400():
    client = _client()
    for sym in ("@@@", "A", "ABCDEFGHIJK", "FP-T"):
        resp = client.post("/scan", json={"symbol": sym})
        assert resp.status_code == 400, sym
        assert "không hợp lệ" in resp.json()["detail"]


def test_scan_negative_threshold_400():
    client = _client()
    resp = client.post("/scan", json={"symbol": "FPT", "threshold_pct": -1})
    assert resp.status_code == 400
    assert "âm" in resp.json()["detail"]


def test_scan_missing_symbol_field_422():
    client = _client()
    resp = client.post("/scan", json={})
    assert resp.status_code == 422


def test_chat_empty_or_whitespace_question_400():
    client = _client()
    for q in ("", "   "):
        resp = client.post("/chat", json={"question": q})
        assert resp.status_code == 400
        assert "rỗng" in resp.json()["detail"]


def test_chat_missing_question_field_422():
    client = _client()
    assert client.post("/chat", json={}).status_code == 422


def test_watchlist_empty_symbol_400():
    client = _client()
    resp = client.post("/watchlist", json={"symbol": "", "threshold_pct": 3})
    assert resp.status_code == 400
    assert "rỗng" in resp.json()["detail"]


def test_watchlist_invalid_symbol_400():
    client = _client()
    resp = client.post("/watchlist", json={"symbol": "!!", "threshold_pct": 3})
    assert resp.status_code == 400
    assert "không hợp lệ" in resp.json()["detail"]


def test_watchlist_negative_threshold_400():
    client = _client()
    resp = client.post("/watchlist", json={"symbol": "VNM", "threshold_pct": -2})
    assert resp.status_code == 400
    assert "âm" in resp.json()["detail"]
    # PATCH ngưỡng âm trên mã đã có
    resp2 = client.patch("/watchlist/FPT", json={"threshold_pct": -1})
    assert resp2.status_code == 400
    assert "âm" in resp2.json()["detail"]


def test_watchlist_symbol_not_found_404():
    """symbol không tồn tại trên watchlist → 404."""
    client = _client()
    resp = client.patch("/watchlist/VNM", json={"threshold_pct": 5})
    assert resp.status_code == 404
    assert "không tìm thấy" in resp.json()["detail"]
    assert client.delete("/watchlist/VNM").status_code == 404


def test_reject_empty_reason_400():
    client = _client()
    resp = client.post("/approvals/a1/reject", json={"reason": "  "})
    assert resp.status_code == 400
    assert "rỗng" in resp.json()["detail"]


def test_valid_inputs_still_ok():
    """Không phá AC quét/chat hợp lệ."""
    client = _client()
    scan = client.post("/scan", json={"symbol": "fpt", "threshold_pct": 3})
    assert scan.status_code == 200
    assert scan.json()["symbol"] == "FPT"
    chat = client.post("/chat", json={"question": "Giá FPT?"})
    assert chat.status_code == 200
    assert chat.json()["answer"]
