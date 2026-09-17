from __future__ import annotations

from fastapi.testclient import TestClient

from src.portfolio_watch.api.deps import AppDeps, set_app_deps
from src.portfolio_watch.application.review_approval import list_pending_approvals
from src.portfolio_watch.domain.entities import WatchlistItem
from src.portfolio_watch.domain.ports import PriceQuote
from src.portfolio_watch.main import app
from src.portfolio_watch.shared.settings import settings
from tests.fakes import (
    FakeMemoryStore,
    FakeNewsSource,
    FakeNotifier,
    FakePriceHistoryStore,
    FakePriceSource,
    FakeWatchlistStore,
)


def _client(
    *,
    items: list[WatchlistItem] | None = None,
    latest: float = 100.0,
    prev: float = 100.0,
) -> tuple[TestClient, FakeWatchlistStore, FakeMemoryStore, FakeNotifier]:
    wl = FakeWatchlistStore(items or [])
    mem = FakeMemoryStore()
    notifier = FakeNotifier()
    set_app_deps(
        AppDeps(
            price_source=FakePriceSource(
                PriceQuote("FPT", latest_close=latest, prev_close=prev)
            ),
            news_source=FakeNewsSource([[]]),
            history_store=FakePriceHistoryStore([]),
            memory_store=mem,
            notifier=notifier,
            watchlist_store=wl,
        )
    )
    return TestClient(app), wl, mem, notifier


def teardown_function():
    set_app_deps(None)


def test_get_watchlist_empty():
    client, _, _, _ = _client()
    resp = client.get("/watchlist")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 0
    assert data["items"] == []


def test_post_and_get_watchlist():
    client, wl, mem, _ = _client()
    resp = client.post(
        "/watchlist", json={"symbol": "fpt", "threshold_pct": 2.5}
    )
    assert resp.status_code == 200
    item = resp.json()
    assert item["symbol"] == "FPT"
    assert item["threshold_pct"] == 2.5

    listed = client.get("/watchlist").json()
    assert listed["count"] == 1
    assert listed["items"][0]["symbol"] == "FPT"
    assert wl.get("default", "FPT").threshold_pct == 2.5
    # CRUD user không qua HITL
    assert list_pending_approvals(mem) == []
    assert mem.alert_events == []


def test_post_watchlist_default_threshold():
    client, _, _, _ = _client()
    resp = client.post("/watchlist", json={"symbol": "VNM"})
    assert resp.status_code == 200
    assert resp.json()["threshold_pct"] == settings.default_alert_threshold_pct


def test_patch_watchlist_threshold():
    client, wl, mem, _ = _client(
        items=[WatchlistItem(symbol="FPT", threshold_pct=3.0, user_id="default")]
    )
    resp = client.patch("/watchlist/fpt", json={"threshold_pct": 5.0})
    assert resp.status_code == 200
    assert resp.json()["symbol"] == "FPT"
    assert resp.json()["threshold_pct"] == 5.0
    assert wl.get("default", "FPT").threshold_pct == 5.0
    assert list_pending_approvals(mem) == []


def test_patch_missing_404():
    client, _, _, _ = _client()
    resp = client.patch("/watchlist/FPT", json={"threshold_pct": 5.0})
    assert resp.status_code == 404
    assert "không tìm thấy" in resp.json()["detail"]


def test_delete_watchlist():
    client, wl, _, _ = _client(
        items=[WatchlistItem(symbol="FPT", threshold_pct=3.0, user_id="default")]
    )
    resp = client.delete("/watchlist/FPT")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    assert wl.get("default", "FPT") is None
    assert client.get("/watchlist").json()["count"] == 0


def test_delete_missing_404():
    client, _, _, _ = _client()
    resp = client.delete("/watchlist/FPT")
    assert resp.status_code == 404


def test_post_whitespace_symbol_400():
    client, _, _, _ = _client()
    resp = client.post("/watchlist", json={"symbol": "   ", "threshold_pct": 3.0})
    assert resp.status_code == 400
    assert "rỗng" in resp.json()["detail"]


def test_negative_threshold_400():
    client, _, _, _ = _client()
    resp = client.post("/watchlist", json={"symbol": "FPT", "threshold_pct": -1})
    assert resp.status_code == 400
    assert "âm" in resp.json()["detail"]


def test_watchlist_low_threshold_drives_scan_alert():
    """product-spec: đặt watchlist ngưỡng thấp → biến động vượt ngưỡng → cảnh báo."""
    client, _, mem, notifier = _client(latest=105.0, prev=100.0)
    add = client.post(
        "/watchlist", json={"symbol": "FPT", "threshold_pct": 1.0}
    )
    assert add.status_code == 200
    assert list_pending_approvals(mem) == []

    # Không ghi đè threshold_pct — scan phải lấy ngưỡng từ watchlist
    scan = client.post("/scan", json={"symbol": "FPT"})
    assert scan.status_code == 200
    data = scan.json()
    assert data["threshold_pct"] == 1.0
    assert data["route"] == "bất thường"
    assert data["alert"] is not None
    assert data["gate1_action"] in ("sent", "pending_approval")
    if data["gate1_action"] == "sent":
        assert len(notifier.sent) == 1
        assert data["alert"]["status"] == "sent"
    else:
        assert data["alert"]["status"] == "pending_approval"
        assert list_pending_approvals(mem)


def test_user_patch_applies_immediately_not_gate2():
    """Sửa ngưỡng qua CRUD (user) áp dụng ngay — khác đề xuất EvalAgent/Gate 2."""
    client, wl, mem, _ = _client(
        items=[WatchlistItem(symbol="FPT", threshold_pct=3.0, user_id="default")]
    )
    resp = client.patch("/watchlist/FPT", json={"threshold_pct": 1.5})
    assert resp.status_code == 200
    assert wl.get("default", "FPT").threshold_pct == 1.5
    assert client.get("/watchlist").json()["items"][0]["threshold_pct"] == 1.5
    assert list_pending_approvals(mem) == []
    assert mem.alert_events == []
