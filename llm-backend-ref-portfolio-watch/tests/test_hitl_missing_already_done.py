"""Phase 5 — HITL: id không tồn tại / đã xử lý → lỗi rõ, không đổi trạng thái.

implementation-plan Phase 5; bổ sung assert side-effect (Notifier, Memory,
Watchlist, event log) so với test API hiện có.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from src.portfolio_watch.api.deps import AppDeps, set_app_deps
from src.portfolio_watch.application.review_approval import (
    approve_pending,
    list_pending_approvals,
    reject_pending,
)
from src.portfolio_watch.domain.entities import (
    AlertStatus,
    FinalAlert,
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


def _gate1(mem: FakeMemoryStore, alert_id: str = "a1") -> None:
    alert = FinalAlert(
        id=alert_id,
        symbol="FPT",
        title="Cảnh báo FPT",
        body="Giá biến động. Bằng chứng: change_pct=5.00%.",
        severity=Severity(
            level=SeverityLevel.MEDIUM,
            confidence=0.4,
            reasoning="mập mờ",
            evidence=["change_pct=5.00%"],
        ),
        status=AlertStatus.PENDING_APPROVAL,
    )
    mem.append_alert_event(
        "default",
        {
            "kind": "pending_approval",
            "gate": "gate1",
            "alert_id": alert_id,
            "symbol": "FPT",
            "status": "pending_approval",
            "alert": alert.model_dump(mode="json"),
        },
    )


def _gate2(mem: FakeMemoryStore, proposal_id: str = "p1") -> None:
    mem.append_alert_event(
        "default",
        {
            "kind": "pending_approval",
            "gate": "gate2",
            "proposal_id": proposal_id,
            "symbol": "FPT",
            "status": "pending_approval",
            "proposed_threshold_pct": 4.5,
            "proposed_related_symbols": ["VNM"],
        },
    )


def _client() -> tuple[TestClient, FakeMemoryStore, FakeNotifier, FakeWatchlistStore]:
    mem = FakeMemoryStore()
    notifier = FakeNotifier()
    wl = FakeWatchlistStore(
        [WatchlistItem(symbol="FPT", threshold_pct=3.0, user_id="default")]
    )
    set_app_deps(
        AppDeps(
            price_source=FakePriceSource(
                PriceQuote("FPT", latest_close=100.0, prev_close=100.0)
            ),
            news_source=FakeNewsSource([[]]),
            history_store=FakePriceHistoryStore([]),
            memory_store=mem,
            notifier=notifier,
            watchlist_store=wl,
        )
    )
    return TestClient(app), mem, notifier, wl


def teardown_function():
    set_app_deps(None)


def _event_count(mem: FakeMemoryStore) -> int:
    return len(mem.alert_events)


def test_api_missing_approve_reject_no_side_effects():
    client, mem, notifier, wl = _client()
    before_events = _event_count(mem)

    ap = client.post("/approvals/nope/approve", json={})
    assert ap.status_code == 404
    assert "không tìm thấy" in ap.json()["detail"]

    rj = client.post("/approvals/nope/reject", json={"reason": "x"})
    assert rj.status_code == 404
    assert "không tìm thấy" in rj.json()["detail"]

    assert notifier.sent == []
    assert mem.rejections == []
    assert _event_count(mem) == before_events
    assert wl.get("default", "FPT").threshold_pct == 3.0
    assert wl.get("default", "VNM") is None
    assert wl.upserts == []
    assert list_pending_approvals(mem) == []


def test_api_approve_twice_second_404_no_extra_send():
    client, mem, notifier, _ = _client()
    _gate1(mem, "a1")
    assert client.post("/approvals/a1/approve", json={}).status_code == 200
    assert len(notifier.sent) == 1
    events_after = _event_count(mem)

    resp = client.post("/approvals/a1/approve", json={})
    assert resp.status_code == 404
    assert "đã xử lý" in resp.json()["detail"]
    assert len(notifier.sent) == 1
    assert _event_count(mem) == events_after
    assert list_pending_approvals(mem) == []


def test_api_reject_twice_second_404_no_extra_rejection():
    client, mem, notifier, _ = _client()
    _gate1(mem, "a1")
    assert (
        client.post("/approvals/a1/reject", json={"reason": "spam"}).status_code
        == 200
    )
    assert len(mem.rejections) == 1
    events_after = _event_count(mem)

    resp = client.post("/approvals/a1/reject", json={"reason": "spam2"})
    assert resp.status_code == 404
    assert "đã xử lý" in resp.json()["detail"]
    assert len(mem.rejections) == 1
    assert mem.rejections[0]["reason"] == "spam"
    assert notifier.sent == []
    assert _event_count(mem) == events_after


def test_api_approve_then_reject_keeps_sent_state():
    client, mem, notifier, _ = _client()
    _gate1(mem, "a1")
    assert client.post("/approvals/a1/approve", json={}).status_code == 200
    events_after = _event_count(mem)

    resp = client.post("/approvals/a1/reject", json={"reason": "muộn rồi"})
    assert resp.status_code == 404
    assert "đã xử lý" in resp.json()["detail"]
    assert len(notifier.sent) == 1
    assert mem.rejections == []
    assert _event_count(mem) == events_after


def test_api_reject_then_approve_does_not_send():
    client, mem, notifier, _ = _client()
    _gate1(mem, "a1")
    assert (
        client.post("/approvals/a1/reject", json={"reason": "tin nhiễu"}).status_code
        == 200
    )
    events_after = _event_count(mem)

    resp = client.post("/approvals/a1/approve", json={})
    assert resp.status_code == 404
    assert "đã xử lý" in resp.json()["detail"]
    assert notifier.sent == []
    assert len(mem.rejections) == 1
    assert _event_count(mem) == events_after


def test_api_gate2_already_done_keeps_watchlist():
    client, mem, notifier, wl = _client()
    _gate2(mem, "p1")
    assert client.post("/approvals/p1/approve", json={}).status_code == 200
    assert wl.get("default", "FPT").threshold_pct == 4.5
    assert wl.get("default", "VNM") is not None
    upserts_after = len(wl.upserts)
    events_after = _event_count(mem)

    again = client.post("/approvals/p1/approve", json={})
    assert again.status_code == 404
    assert "đã xử lý" in again.json()["detail"]

    reject_late = client.post(
        "/approvals/p1/reject", json={"reason": "muộn"}
    )
    assert reject_late.status_code == 404

    assert wl.get("default", "FPT").threshold_pct == 4.5
    assert len(wl.upserts) == upserts_after
    assert notifier.sent == []
    assert mem.rejections == []
    assert _event_count(mem) == events_after


def test_api_gate2_reject_then_approve_keeps_old_threshold():
    client, mem, notifier, wl = _client()
    _gate2(mem, "p1")
    assert (
        client.post(
            "/approvals/p1/reject", json={"reason": "giữ ngưỡng cũ"}
        ).status_code
        == 200
    )
    events_after = _event_count(mem)

    resp = client.post("/approvals/p1/approve", json={})
    assert resp.status_code == 404
    assert "đã xử lý" in resp.json()["detail"]
    assert wl.get("default", "FPT").threshold_pct == 3.0
    assert wl.get("default", "VNM") is None
    assert wl.upserts == []
    assert notifier.sent == []
    assert len(mem.rejections) == 1
    assert _event_count(mem) == events_after


def test_app_layer_missing_already_done_no_mutation():
    """Cùng rule ở application layer (không qua HTTP)."""
    mem = FakeMemoryStore()
    notifier = FakeNotifier()
    wl = FakeWatchlistStore(
        [WatchlistItem(symbol="FPT", threshold_pct=3.0, user_id="default")]
    )

    missing = approve_pending(
        "nope", memory_store=mem, notifier=notifier, watchlist_store=wl
    )
    assert missing.ok is False
    assert "không tìm thấy" in (missing.error or "")
    assert notifier.sent == []
    assert mem.alert_events == []

    _gate1(mem, "a1")
    first = approve_pending(
        "a1", memory_store=mem, notifier=notifier, watchlist_store=wl
    )
    assert first.ok is True
    n_events = len(mem.alert_events)

    second = approve_pending(
        "a1", memory_store=mem, notifier=notifier, watchlist_store=wl
    )
    assert second.ok is False
    assert "đã xử lý" in (second.error or "")
    assert len(notifier.sent) == 1
    assert len(mem.alert_events) == n_events

    cross = reject_pending(
        "a1", "muộn", memory_store=mem, watchlist_store=wl
    )
    assert cross.ok is False
    assert "đã xử lý" in (cross.error or "")
    assert mem.rejections == []
    assert len(mem.alert_events) == n_events


def test_resolution_with_alert_id_only_still_blocks_reapprove():
    """Resolution chỉ có alert_id (thiếu approval_id) vẫn tính đã xử lý."""
    mem = FakeMemoryStore()
    notifier = FakeNotifier()
    wl = FakeWatchlistStore()
    _gate1(mem, "a1")
    mem.append_alert_event(
        "default",
        {"kind": "resolution", "alert_id": "a1", "gate": "gate1", "action": "approved"},
    )
    assert list_pending_approvals(mem) == []
    result = approve_pending(
        "a1", memory_store=mem, notifier=notifier, watchlist_store=wl
    )
    assert result.ok is False
    assert "đã xử lý" in (result.error or "")
    assert notifier.sent == []


def test_api_gate2_reject_twice_no_watchlist_change():
    client, mem, notifier, wl = _client()
    _gate2(mem, "p1")
    assert (
        client.post(
            "/approvals/p1/reject", json={"reason": "giữ ngưỡng"}
        ).status_code
        == 200
    )
    events_after = _event_count(mem)

    resp = client.post("/approvals/p1/reject", json={"reason": "lần 2"})
    assert resp.status_code == 404
    assert "đã xử lý" in resp.json()["detail"]
    assert wl.get("default", "FPT").threshold_pct == 3.0
    assert wl.upserts == []
    assert notifier.sent == []
    assert len(mem.rejections) == 1
    assert _event_count(mem) == events_after


def test_api_already_done_empty_reason_still_404():
    """Id đã xử lý + lý do rỗng → 404 đã xử lý (không 400 lý do rỗng)."""
    client, mem, notifier, _ = _client()
    _gate1(mem, "a1")
    assert client.post("/approvals/a1/approve", json={}).status_code == 200
    events_after = _event_count(mem)

    resp = client.post("/approvals/a1/reject", json={"reason": ""})
    assert resp.status_code == 404
    assert "đã xử lý" in resp.json()["detail"]
    assert mem.rejections == []
    assert len(notifier.sent) == 1
    assert _event_count(mem) == events_after


def test_api_missing_empty_reason_still_404():
    client, mem, notifier, wl = _client()
    resp = client.post("/approvals/nope/reject", json={"reason": "  "})
    assert resp.status_code == 404
    assert "không tìm thấy" in resp.json()["detail"]
    assert mem.rejections == []
    assert notifier.sent == []
    assert wl.upserts == []
