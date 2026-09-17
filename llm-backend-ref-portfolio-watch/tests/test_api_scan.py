from __future__ import annotations

from fastapi.testclient import TestClient

from src.portfolio_watch.api.deps import AppDeps, set_app_deps
from src.portfolio_watch.api.routers import scan as scan_router_mod
from src.portfolio_watch.domain.entities import (
    EventRoute,
    Severity,
    SeverityLevel,
    WatchlistItem,
)
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


def _client_with_fakes(
    *,
    latest: float,
    prev: float,
) -> tuple[TestClient, FakeNotifier, FakeMemoryStore]:
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
            watchlist_store=FakeWatchlistStore(
                [WatchlistItem(symbol="FPT", threshold_pct=3.0)]
            ),
        )
    )
    return TestClient(app), notifier, mem


def teardown_function():
    set_app_deps(None)


def test_post_scan_normal():
    """test-plan #1: POST /scan bình thường → không alert."""
    client, notifier, mem = _client_with_fakes(latest=101.0, prev=100.0)
    resp = client.post("/scan", json={"symbol": "FPT", "threshold_pct": 3.0})
    assert resp.status_code == 200
    data = resp.json()
    assert data["symbol"] == "FPT"
    assert data["route"] == EventRoute.NORMAL.value
    assert data["alert"] is None
    assert data["severity"] is None
    assert data["gate1_action"] is None
    assert data["gate2_pending"] is False
    assert data["pending_events"] == []
    assert notifier.sent == []
    assert data["price"]["change_pct"] == 1.0
    assert "price" in data and "news" in data and "route" in data


def test_post_scan_abnormal_auto_send():
    """test-plan #2: confidence cao → gửi, không chờ duyệt."""
    client, notifier, _mem = _client_with_fakes(latest=105.0, prev=100.0)
    resp = client.post("/scan", json={"symbol": "fpt", "threshold_pct": 3.0})
    assert resp.status_code == 200
    data = resp.json()
    assert data["route"] == EventRoute.ABNORMAL.value
    assert data["gate1_action"] == "sent"
    assert data["severity"] is not None
    assert data["alert"] is not None
    assert data["alert"]["status"] == "sent"
    assert data["gate2_pending"] is False
    assert data["pending_events"] == []
    assert len(notifier.sent) == 1


def test_post_scan_low_confidence_pending():
    """test-plan #3 (phần scan): confidence thấp → pending_approval."""

    class LowConfEval:
        def needs_history(self, price, news, history):
            return False

        def build_severity(self, price, news, history):
            return Severity(
                level=SeverityLevel.MEDIUM,
                confidence=0.4,
                reasoning="mập mờ",
                evidence=["change_pct=5.00%"],
            )

    real = scan_router_mod.scan_symbol

    def wrapped(symbol, **kwargs):
        return real(symbol, eval_brain=LowConfEval(), **kwargs)

    scan_router_mod.scan_symbol = wrapped  # type: ignore[assignment]
    try:
        client, notifier, _mem = _client_with_fakes(latest=105.0, prev=100.0)
        resp = client.post("/scan", json={"symbol": "FPT", "threshold_pct": 3.0})
    finally:
        scan_router_mod.scan_symbol = real  # type: ignore[assignment]

    assert resp.status_code == 200
    data = resp.json()
    assert data["gate1_action"] == "pending_approval"
    assert data["alert"] is not None
    assert data["alert"]["status"] == "pending_approval"
    assert data["pending_events"]
    assert any(e.get("gate") == "gate1" for e in data["pending_events"])
    assert notifier.sent == []


def test_post_scan_gate2_pending_high_confidence():
    """test-plan #4: đề xuất ngưỡng → gate2_pending dù auto-send."""
    client, notifier, _mem = _client_with_fakes(latest=108.0, prev=100.0)
    resp = client.post("/scan", json={"symbol": "FPT", "threshold_pct": 3.0})
    assert resp.status_code == 200
    data = resp.json()
    assert data["gate1_action"] == "sent"
    assert data["gate2_pending"] is True
    assert data["severity"] is not None
    assert data["severity"]["proposed_threshold_pct"] is not None
    assert any(e.get("gate") == "gate2" for e in data["pending_events"])
    assert len(notifier.sent) == 1


def test_post_scan_empty_symbol_400():
    client, _, _ = _client_with_fakes(latest=100.0, prev=100.0)
    resp = client.post("/scan", json={"symbol": ""})
    assert resp.status_code == 400
    assert "rỗng" in resp.json()["detail"]


def test_post_scan_whitespace_symbol_400():
    client, _, _ = _client_with_fakes(latest=100.0, prev=100.0)
    resp = client.post("/scan", json={"symbol": "   "})
    assert resp.status_code == 400
    assert "rỗng" in resp.json()["detail"]
