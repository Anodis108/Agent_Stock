from __future__ import annotations

from fastapi.testclient import TestClient

from src.portfolio_watch.api.deps import AppDeps, set_app_deps
from src.portfolio_watch.api.routers import scan as scan_router_mod
from src.portfolio_watch.application.review_approval import list_pending_approvals
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


def _gate1_pending(mem: FakeMemoryStore, alert_id: str = "a1") -> None:
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


def _gate2_pending(mem: FakeMemoryStore, proposal_id: str = "p1") -> None:
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


def _client(
    *,
    latest: float = 100.0,
    prev: float = 100.0,
) -> tuple[TestClient, FakeMemoryStore, FakeNotifier, FakeWatchlistStore]:
    mem = FakeMemoryStore()
    notifier = FakeNotifier()
    wl = FakeWatchlistStore(
        [WatchlistItem(symbol="FPT", threshold_pct=3.0, user_id="default")]
    )
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
    return TestClient(app), mem, notifier, wl


def teardown_function():
    set_app_deps(None)


def _scan_low_confidence(client: TestClient) -> dict:
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
        resp = client.post("/scan", json={"symbol": "FPT", "threshold_pct": 3.0})
    finally:
        scan_router_mod.scan_symbol = real  # type: ignore[assignment]
    assert resp.status_code == 200
    return resp.json()


def test_get_approvals_lists_pending():
    client, mem, _, _ = _client()
    _gate1_pending(mem, "a1")
    _gate2_pending(mem, "p1")
    resp = client.get("/approvals")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 2
    ids = {i["approval_id"] for i in data["items"]}
    assert ids == {"a1", "p1"}
    gate1 = next(i for i in data["items"] if i["approval_id"] == "a1")
    assert gate1.get("alert") is not None
    assert gate1["alert"]["status"] == "pending_approval"


def test_approve_gate1_sends_alert():
    """HITL Gate 1: approve → đã gửi."""
    client, mem, notifier, _ = _client()
    _gate1_pending(mem, "a1")
    resp = client.post("/approvals/a1/approve", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["gate"] == "gate1"
    assert data["alert"]["status"] == "sent"
    assert len(notifier.sent) == 1
    assert list_pending_approvals(mem) == []
    assert client.get("/approvals").json()["count"] == 0


def test_reject_gate1_records_reason():
    """HITL Gate 1: reject → không gửi, lý do lưu Memory."""
    client, mem, notifier, _ = _client()
    _gate1_pending(mem, "a1")
    resp = client.post("/approvals/a1/reject", json={"reason": "tin nhiễu"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["alert"]["status"] == "rejected"
    assert data["alert"]["reject_reason"] == "tin nhiễu"
    assert notifier.sent == []
    assert mem.rejections[0]["reason"] == "tin nhiễu"
    assert mem.rejections[0]["gate"] == "gate1"
    assert list_pending_approvals(mem) == []


def test_scan_then_approve_e2e():
    """test-plan #3: POST /scan pending → POST /approvals/.../approve → sent."""
    client, mem, notifier, _ = _client(latest=105.0, prev=100.0)
    scan = _scan_low_confidence(client)
    assert scan["gate1_action"] == "pending_approval"
    assert notifier.sent == []

    listed = client.get("/approvals").json()
    assert listed["count"] >= 1
    gate1 = next(i for i in listed["items"] if i.get("gate") == "gate1")
    aid = gate1["approval_id"]

    resp = client.post(f"/approvals/{aid}/approve", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["alert"]["status"] == "sent"
    assert len(notifier.sent) == 1
    assert list_pending_approvals(mem) == []
    assert client.get("/approvals").json()["count"] == 0


def test_scan_then_reject_e2e():
    """test-plan #3: POST /scan pending → reject → không gửi, lý do lưu."""
    client, mem, notifier, _ = _client(latest=105.0, prev=100.0)
    scan = _scan_low_confidence(client)
    assert scan["gate1_action"] == "pending_approval"
    aid = next(
        i["approval_id"]
        for i in client.get("/approvals").json()["items"]
        if i.get("gate") == "gate1"
    )

    resp = client.post(
        f"/approvals/{aid}/reject", json={"reason": "tin nhiễu"}
    )
    assert resp.status_code == 200
    assert resp.json()["alert"]["reject_reason"] == "tin nhiễu"
    assert notifier.sent == []
    assert mem.rejections[0]["reason"] == "tin nhiễu"
    assert list_pending_approvals(mem) == []


def test_approve_gate2_updates_watchlist():
    client, mem, notifier, wl = _client()
    _gate2_pending(mem, "p1")
    resp = client.post("/approvals/p1/approve", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["gate"] == "gate2"
    assert data["watchlist_updates"]
    assert wl.get("default", "FPT").threshold_pct == 4.5
    assert wl.get("default", "VNM") is not None
    assert notifier.sent == []
    assert list_pending_approvals(mem) == []


def test_reject_gate2_keeps_watchlist():
    """HITL Gate 2: reject → giữ cấu hình cũ, lý do ghi Memory."""
    client, mem, _, wl = _client()
    _gate2_pending(mem, "p1")
    resp = client.post(
        "/approvals/p1/reject", json={"reason": "ngưỡng quá thấp"}
    )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    assert resp.json()["gate"] == "gate2"
    assert wl.get("default", "FPT").threshold_pct == 3.0
    assert wl.get("default", "VNM") is None
    assert wl.upserts == []
    assert mem.rejections[0]["gate"] == "gate2"
    assert mem.rejections[0]["reason"] == "ngưỡng quá thấp"
    assert list_pending_approvals(mem) == []


def test_reject_empty_reason_400():
    client, mem, _, _ = _client()
    _gate1_pending(mem, "a1")
    for payload in ({"reason": ""}, {"reason": "   "}):
        resp = client.post("/approvals/a1/reject", json=payload)
        assert resp.status_code == 400
        assert "rỗng" in resp.json()["detail"]
    assert len(list_pending_approvals(mem)) == 1
    assert mem.rejections == []


def test_approve_missing_404():
    client, _, _, _ = _client()
    resp = client.post("/approvals/nope/approve", json={})
    assert resp.status_code == 404
    assert "không tìm thấy" in resp.json()["detail"]


def test_reject_missing_404():
    client, _, _, _ = _client()
    resp = client.post(
        "/approvals/nope/reject", json={"reason": "x"}
    )
    assert resp.status_code == 404
    assert "không tìm thấy" in resp.json()["detail"]


def test_approve_already_done_404():
    client, mem, _, _ = _client()
    _gate1_pending(mem, "a1")
    assert client.post("/approvals/a1/approve", json={}).status_code == 200
    resp = client.post("/approvals/a1/approve", json={})
    assert resp.status_code == 404
    assert "đã xử lý" in resp.json()["detail"]


def test_reject_already_done_404():
    client, mem, _, _ = _client()
    _gate1_pending(mem, "a1")
    assert client.post(
        "/approvals/a1/reject", json={"reason": "spam"}
    ).status_code == 200
    resp = client.post(
        "/approvals/a1/reject", json={"reason": "spam2"}
    )
    assert resp.status_code == 404
    assert "đã xử lý" in resp.json()["detail"]
