from __future__ import annotations

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
from tests.fakes import FakeMemoryStore, FakeNotifier, FakeWatchlistStore


def _gate1_pending(mem: FakeMemoryStore, alert_id: str = "a1") -> FinalAlert:
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
    return alert


def _gate2_pending(
    mem: FakeMemoryStore,
    proposal_id: str = "p1",
    *,
    thr: float = 4.0,
    related: list[str] | None = None,
) -> None:
    mem.append_alert_event(
        "default",
        {
            "kind": "pending_approval",
            "gate": "gate2",
            "proposal_id": proposal_id,
            "symbol": "FPT",
            "status": "pending_approval",
            "proposed_threshold_pct": thr,
            "proposed_related_symbols": related or ["VNM"],
            "severity": {
                "level": "high",
                "confidence": 0.9,
                "reasoning": "biến động lớn",
                "evidence": ["change_pct=8.00%"],
            },
        },
    )


def test_list_pending_approvals():
    mem = FakeMemoryStore()
    _gate1_pending(mem, "a1")
    _gate2_pending(mem, "p1")
    pending = list_pending_approvals(mem)
    assert len(pending) == 2
    ids = {p["approval_id"] for p in pending}
    assert ids == {"a1", "p1"}


def test_approve_gate1_sends_alert():
    mem = FakeMemoryStore()
    notifier = FakeNotifier()
    wl = FakeWatchlistStore(
        [WatchlistItem(symbol="FPT", threshold_pct=3.0, user_id="default")]
    )
    _gate1_pending(mem, "a1")

    result = approve_pending(
        "a1", memory_store=mem, notifier=notifier, watchlist_store=wl
    )
    assert result.ok is True
    assert result.gate == "gate1"
    assert len(notifier.sent) == 1
    assert notifier.sent[0].status == AlertStatus.SENT
    assert list_pending_approvals(mem) == []


def test_reject_gate1_records_reason_no_send():
    mem = FakeMemoryStore()
    notifier = FakeNotifier()
    wl = FakeWatchlistStore()
    _gate1_pending(mem, "a1")

    result = reject_pending(
        "a1", "tin nhiễu", memory_store=mem, watchlist_store=wl
    )
    assert result.ok is True
    assert result.gate == "gate1"
    assert notifier.sent == []
    assert result.alert is not None
    assert result.alert.status == AlertStatus.REJECTED
    assert result.alert.reject_reason == "tin nhiễu"
    assert len(mem.rejections) == 1
    assert mem.rejections[0]["reason"] == "tin nhiễu"
    assert mem.rejections[0]["gate"] == "gate1"
    assert list_pending_approvals(mem) == []


def test_reject_empty_reason_fails():
    mem = FakeMemoryStore()
    _gate1_pending(mem, "a1")
    result = reject_pending("a1", "  ", memory_store=mem)
    assert result.ok is False
    assert "rỗng" in (result.error or "")
    assert mem.rejections == []
    assert len(list_pending_approvals(mem)) == 1


def test_approve_gate2_updates_watchlist():
    mem = FakeMemoryStore()
    notifier = FakeNotifier()
    wl = FakeWatchlistStore(
        [WatchlistItem(symbol="FPT", threshold_pct=3.0, user_id="default")]
    )
    _gate2_pending(mem, "p1", thr=4.5, related=["VNM"])

    result = approve_pending(
        "p1", memory_store=mem, notifier=notifier, watchlist_store=wl
    )
    assert result.ok is True
    assert result.gate == "gate2"
    assert wl.get("default", "FPT").threshold_pct == 4.5
    assert wl.get("default", "VNM") is not None
    assert wl.get("default", "VNM").threshold_pct == 4.5
    assert notifier.sent == []  # Gate 2 không gửi alert
    assert list_pending_approvals(mem) == []


def test_reject_gate2_keeps_watchlist():
    mem = FakeMemoryStore()
    wl = FakeWatchlistStore(
        [WatchlistItem(symbol="FPT", threshold_pct=3.0, user_id="default")]
    )
    _gate2_pending(mem, "p1", thr=9.0)

    result = reject_pending(
        "p1", "ngưỡng quá thấp", memory_store=mem, watchlist_store=wl
    )
    assert result.ok is True
    assert wl.get("default", "FPT").threshold_pct == 3.0
    assert wl.upserts == []
    assert mem.rejections[0]["gate"] == "gate2"
    assert mem.rejections[0]["reason"] == "ngưỡng quá thấp"
    assert list_pending_approvals(mem) == []


def test_approve_missing_or_already_done():
    mem = FakeMemoryStore()
    notifier = FakeNotifier()
    wl = FakeWatchlistStore()
    missing = approve_pending(
        "nope", memory_store=mem, notifier=notifier, watchlist_store=wl
    )
    assert missing.ok is False
    assert "không tìm thấy" in (missing.error or "")

    _gate1_pending(mem, "a1")
    first = approve_pending(
        "a1", memory_store=mem, notifier=notifier, watchlist_store=wl
    )
    assert first.ok is True
    assert first.alert is not None
    assert first.alert.status == AlertStatus.SENT
    second = approve_pending(
        "a1", memory_store=mem, notifier=notifier, watchlist_store=wl
    )
    assert second.ok is False
    assert "đã xử lý" in (second.error or "")


def test_reject_missing_or_already_done():
    mem = FakeMemoryStore()
    wl = FakeWatchlistStore()
    missing = reject_pending("nope", "x", memory_store=mem, watchlist_store=wl)
    assert missing.ok is False
    assert "không tìm thấy" in (missing.error or "")

    _gate1_pending(mem, "a1")
    first = reject_pending("a1", "spam", memory_store=mem, watchlist_store=wl)
    assert first.ok is True
    second = reject_pending("a1", "spam2", memory_store=mem, watchlist_store=wl)
    assert second.ok is False
    assert "đã xử lý" in (second.error or "")
    assert len(mem.rejections) == 1


def test_gate1_approve_sets_sent_even_if_notifier_skips_status():
    class SilentNotifier:
        def send(self, alert):
            return None  # không đổi status

    mem = FakeMemoryStore()
    wl = FakeWatchlistStore()
    _gate1_pending(mem, "a1")
    result = approve_pending(
        "a1", memory_store=mem, notifier=SilentNotifier(), watchlist_store=wl
    )
    assert result.ok is True
    assert result.alert is not None
    assert result.alert.status == AlertStatus.SENT
