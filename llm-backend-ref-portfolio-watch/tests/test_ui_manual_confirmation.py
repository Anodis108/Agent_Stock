"""Xác nhận Phase 4 — luồng UI (cùng endpoint mà web/app.js gọi).

Tương đương checklist:
  quét 1 mã → thấy kết quả; hỏi 1 câu → thấy trả lời;
  chờ duyệt → approve/reject cập nhật đúng.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from src.portfolio_watch.api.deps import AppDeps, set_app_deps
from src.portfolio_watch.api.routers import scan as scan_router_mod
from src.portfolio_watch.application.review_approval import list_pending_approvals
from src.portfolio_watch.domain.entities import EventRoute, Severity, SeverityLevel, WatchlistItem
from src.portfolio_watch.domain.ports import NewsItem, PriceQuote
from src.portfolio_watch.main import app
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
    latest: float = 105.0,
    prev: float = 100.0,
    news_batches: list | None = None,
) -> tuple[TestClient, FakeMemoryStore, FakeNotifier]:
    mem = FakeMemoryStore()
    notifier = FakeNotifier()
    set_app_deps(
        AppDeps(
            price_source=FakePriceSource(
                PriceQuote("FPT", latest_close=latest, prev_close=prev)
            ),
            news_source=FakeNewsSource(news_batches or [[]]),
            history_store=FakePriceHistoryStore([]),
            memory_store=mem,
            notifier=notifier,
            watchlist_store=FakeWatchlistStore(
                [WatchlistItem(symbol="FPT", threshold_pct=3.0)]
            ),
        )
    )
    return TestClient(app), mem, notifier


def teardown_function():
    set_app_deps(None)


def _with_low_conf_eval(client: TestClient, payload: dict) -> dict:
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
        resp = client.post("/scan", json=payload)
    finally:
        scan_router_mod.scan_symbol = real  # type: ignore[assignment]
    assert resp.status_code == 200
    return resp.json()


def test_ui_page_loads_three_zones():
    client, _, _ = _client()
    html = client.get("/").text
    assert 'id="chat"' in html
    assert 'id="watchlist"' in html
    assert 'id="approvals"' in html
    assert "scan-form" in html
    js = client.get("/app.js").text
    assert "scanSymbol" in js and "sendChat" in js and "approveAlert" in js
    assert "showScanResult" in js and "severity" in js


def test_manual_scan_normal_no_alert():
    """test-plan #1 + checklist: quét bình thường → UI không có alert."""
    client, mem, notifier = _client(latest=101.0, prev=100.0)
    wl = client.get("/watchlist").json()
    assert any(i["symbol"] == "FPT" for i in wl["items"])

    scan = client.post("/scan", json={"symbol": "FPT"}).json()
    assert scan["symbol"] == "FPT"
    assert scan["route"] == EventRoute.NORMAL.value
    assert scan["alert"] is None
    assert scan["severity"] is None
    assert scan["gate1_action"] is None
    assert "price" in scan and scan["price"]["change_pct"] == 1.0
    assert "news_count" in scan
    assert client.get("/approvals").json()["count"] == 0
    assert notifier.sent == []
    assert list_pending_approvals(mem) == []


def test_manual_scan_abnormal_shows_full_flow_fields():
    """product-spec: quét bất thường → giá/tin/phân loại/đánh giá/cảnh báo/gate."""
    news = [NewsItem(title="FPT biến động mạnh", snippet="tăng", symbol="FPT")]
    client, _, notifier = _client(
        latest=105.0, prev=100.0, news_batches=[news]
    )
    scan = client.post("/scan", json={"symbol": "FPT", "threshold_pct": 3.0}).json()
    assert scan["route"] == EventRoute.ABNORMAL.value
    assert scan["price"]["latest_close"] == 105.0
    assert scan["news_count"] >= 1
    assert scan["severity"] is not None
    assert "confidence" in scan["severity"]
    assert scan["alert"] is not None
    assert scan["gate1_action"] in ("sent", "pending_approval")
    # field UI showScanResult đọc
    assert "reason" in scan
    assert "gate2_pending" in scan
    if scan["gate1_action"] == "sent":
        assert len(notifier.sent) == 1
        assert client.get("/approvals").json()["count"] == 0 or scan["gate2_pending"]


def test_manual_scan_high_confidence_auto_send():
    """test-plan #2: confidence cao → gửi, không Gate 1 pending (UI list trống gate1)."""
    client, mem, notifier = _client(latest=105.0, prev=100.0)
    scan = client.post("/scan", json={"symbol": "FPT", "threshold_pct": 3.0}).json()
    assert scan["route"] == EventRoute.ABNORMAL.value
    assert scan["gate1_action"] == "sent"
    assert scan["alert"]["status"] == "sent"
    assert len(notifier.sent) == 1
    gate1_pending = [
        i
        for i in client.get("/approvals").json()["items"]
        if i.get("gate") == "gate1"
    ]
    assert gate1_pending == []
    assert list_pending_approvals(mem) == [] or all(
        e.get("gate") != "gate1" for e in list_pending_approvals(mem)
    )


def test_manual_chat_shows_answer():
    """test-plan #5 + checklist: hỏi giá → trả lời, không HITL."""
    client, mem, _ = _client()
    resp = client.post("/chat", json={"question": "Giá FPT hiện tại?"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["answer"]
    assert "105" in data["answer"] or "5.00" in data["answer"]
    assert data["symbol"] == "FPT"
    assert data["hitl_used"] is False
    assert data["pending_approvals_created"] == 0
    assert list_pending_approvals(mem) == []


def test_manual_pending_approve_updates_state():
    """test-plan #3 + checklist: pending → approve → sent, list UI trống."""
    client, mem, notifier = _client(latest=105.0, prev=100.0)
    scan = _with_low_conf_eval(
        client, {"symbol": "FPT", "threshold_pct": 3.0}
    )
    assert scan["gate1_action"] == "pending_approval"
    assert scan["alert"]["status"] == "pending_approval"

    listed = client.get("/approvals").json()
    assert listed["count"] >= 1
    item = next(i for i in listed["items"] if i.get("gate") == "gate1")
    # field renderApprovals cần
    assert item.get("approval_id")
    assert item.get("symbol") or (item.get("alert") or {}).get("symbol")

    ok = client.post(f"/approvals/{item['approval_id']}/approve", json={})
    assert ok.status_code == 200
    assert ok.json()["alert"]["status"] == "sent"
    assert len(notifier.sent) == 1
    assert client.get("/approvals").json()["count"] == 0
    assert list_pending_approvals(mem) == []


def test_manual_pending_reject_updates_state():
    """test-plan #3 + checklist: reject → không gửi, lý do lưu, list trống."""
    client, mem, notifier = _client(latest=105.0, prev=100.0)
    _with_low_conf_eval(client, {"symbol": "FPT", "threshold_pct": 3.0})

    aid = next(
        i["approval_id"]
        for i in client.get("/approvals").json()["items"]
        if i.get("gate") == "gate1"
    )
    rej = client.post(
        f"/approvals/{aid}/reject", json={"reason": "tin nhiễu"}
    )
    assert rej.status_code == 200
    assert rej.json()["alert"]["reject_reason"] == "tin nhiễu"
    assert notifier.sent == []
    assert mem.rejections[0]["reason"] == "tin nhiễu"
    assert client.get("/approvals").json()["count"] == 0
    assert list_pending_approvals(mem) == []
