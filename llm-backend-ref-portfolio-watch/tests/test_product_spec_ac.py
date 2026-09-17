"""Phase 5 — Rà lại toàn bộ acceptance criteria trong product-spec.md.

Mỗi test map 1 bullet AC; chạy qua HTTP API (cùng đường UI/demo dùng).
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from src.portfolio_watch.api.deps import AppDeps, set_app_deps
from src.portfolio_watch.api.routers import scan as scan_router_mod
from src.portfolio_watch.application.review_approval import list_pending_approvals
from src.portfolio_watch.domain.entities import Severity, SeverityLevel, WatchlistItem
from src.portfolio_watch.domain.guardrails.output_checks import check_output
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
    latest: float = 100.0,
    prev: float = 100.0,
    news: list[NewsItem] | None = None,
    wl_items: list[WatchlistItem] | None = None,
) -> tuple[TestClient, FakeMemoryStore, FakeNotifier, FakeWatchlistStore]:
    mem = FakeMemoryStore()
    notifier = FakeNotifier()
    wl = FakeWatchlistStore(
        wl_items
        if wl_items is not None
        else [WatchlistItem(symbol="FPT", threshold_pct=3.0, user_id="default")]
    )
    set_app_deps(
        AppDeps(
            price_source=FakePriceSource(
                PriceQuote("FPT", latest_close=latest, prev_close=prev)
            ),
            news_source=FakeNewsSource([news or []]),
            history_store=FakePriceHistoryStore([]),
            memory_store=mem,
            notifier=notifier,
            watchlist_store=wl,
        )
    )
    return TestClient(app), mem, notifier, wl


def teardown_function():
    set_app_deps(None)


def _scan_with_eval(client: TestClient, payload: dict, brain) -> dict:
    real = scan_router_mod.scan_symbol

    def wrapped(symbol, **kwargs):
        return real(symbol, eval_brain=brain, **kwargs)

    scan_router_mod.scan_symbol = wrapped  # type: ignore[assignment]
    try:
        resp = client.post("/scan", json=payload)
    finally:
        scan_router_mod.scan_symbol = real  # type: ignore[assignment]
    assert resp.status_code == 200
    return resp.json()


def test_ac1_scan_shows_full_pipeline():
    """AC: quét ngay 1 mã → giá, tin, phân loại; bất thường → đánh giá + cảnh báo + gate."""
    # Nhánh bình thường: vẫn thấy giá / tin / phân loại, không alert
    client_n, _, n_n, _ = _client(latest=101.0, prev=100.0)
    normal = client_n.post("/scan", json={"symbol": "FPT"}).json()
    assert normal["symbol"] == "FPT"
    assert normal["price"]["change_pct"] == 1.0
    assert normal["route"] == "bình thường"
    assert normal["alert"] is None
    assert normal["severity"] is None
    assert n_n.sent == []

    news = [NewsItem(title="FPT tin liên quan", snippet="biến động", symbol="FPT")]
    client, _, notifier, _ = _client(latest=105.0, prev=100.0, news=news)
    resp = client.post("/scan", json={"symbol": "FPT"})
    assert resp.status_code == 200
    data = resp.json()

    assert data["symbol"] == "FPT"
    assert data["price"]["latest_close"] == 105.0
    assert data["price"]["change_pct"] == 5.0
    assert data["news_count"] >= 1
    assert data["route"] == "bất thường"
    assert data["reason"]
    assert data["severity"] is not None
    assert data["alert"] is not None
    assert data["gate1_action"] in ("sent", "pending_approval")
    assert data["alert"]["status"] in ("sent", "pending_approval")
    if data["gate1_action"] == "sent":
        assert len(notifier.sent) == 1


def test_ac2_watchlist_low_threshold_triggers_alert_status():
    """AC: đặt ngưỡng thấp trên watchlist → biến động vượt ngưỡng → chờ duyệt/đã gửi."""
    # Đặt qua API (đúng chữ "Đặt watchlist")
    client, mem, notifier, wl = _client(
        latest=102.0, prev=100.0, wl_items=[]
    )
    posted = client.post(
        "/watchlist", json={"symbol": "FPT", "threshold_pct": 1.0}
    )
    assert posted.status_code == 200
    assert wl.get("default", "FPT").threshold_pct == 1.0

    data = client.post("/scan", json={"symbol": "FPT"}).json()
    assert data["threshold_pct"] == 1.0
    assert data["route"] == "bất thường"
    assert data["gate1_action"] in ("sent", "pending_approval")
    if data["gate1_action"] == "sent":
        assert data["alert"]["status"] == "sent"
        assert len(notifier.sent) == 1
    else:
        assert data["alert"]["status"] == "pending_approval"
        assert notifier.sent == []
        assert any(e.get("gate") == "gate1" for e in list_pending_approvals(mem))

    # Ngưỡng cao hơn biến động → không cảnh báo
    client_hi, mem_hi, n_hi, _ = _client(
        latest=102.0,
        prev=100.0,
        wl_items=[],
    )
    assert (
        client_hi.post(
            "/watchlist", json={"symbol": "FPT", "threshold_pct": 10.0}
        ).status_code
        == 200
    )
    normal = client_hi.post("/scan", json={"symbol": "FPT"}).json()
    assert normal["threshold_pct"] == 10.0
    assert normal["route"] == "bình thường"
    assert normal["alert"] is None
    assert n_hi.sent == []
    assert list_pending_approvals(mem_hi) == []


def test_ac3_approve_reject_updates_status_and_reason():
    """AC: approve/reject qua API → trạng thái đúng; lý do reject được ghi."""

    class LowConf:
        def needs_history(self, price, news, history):
            return False

        def build_severity(self, price, news, history):
            return Severity(
                level=SeverityLevel.MEDIUM,
                confidence=0.4,
                reasoning="mập mờ",
                evidence=["change_pct=5.00%"],
            )

    # approve path
    client_a, mem_a, n_a, _ = _client(latest=105.0, prev=100.0)
    scan_a = _scan_with_eval(
        client_a, {"symbol": "FPT", "threshold_pct": 3.0}, LowConf()
    )
    assert scan_a["gate1_action"] == "pending_approval"
    aid = next(
        i["approval_id"]
        for i in client_a.get("/approvals").json()["items"]
        if i.get("gate") == "gate1"
    )
    ap = client_a.post(f"/approvals/{aid}/approve", json={})
    assert ap.status_code == 200
    assert ap.json()["alert"]["status"] == "sent"
    assert len(n_a.sent) == 1
    assert list_pending_approvals(mem_a) == []

    # reject path
    client_r, mem_r, n_r, _ = _client(latest=105.0, prev=100.0)
    _scan_with_eval(client_r, {"symbol": "FPT", "threshold_pct": 3.0}, LowConf())
    rid = next(
        i["approval_id"]
        for i in client_r.get("/approvals").json()["items"]
        if i.get("gate") == "gate1"
    )
    rj = client_r.post(
        f"/approvals/{rid}/reject", json={"reason": "tin nhiễu"}
    )
    assert rj.status_code == 200
    assert rj.json()["alert"]["status"] == "rejected"
    assert rj.json()["alert"]["reject_reason"] == "tin nhiễu"
    assert n_r.sent == []
    assert mem_r.rejections[0]["reason"] == "tin nhiễu"


def test_ac4_threshold_proposal_always_gate2_not_auto_applied():
    """AC: đề xuất đổi ngưỡng → luôn chờ duyệt Gate 2, không tự áp dụng."""
    client, mem, notifier, wl = _client(latest=108.0, prev=100.0)
    before = wl.get("default", "FPT").threshold_pct
    data = client.post(
        "/scan", json={"symbol": "FPT", "threshold_pct": 3.0}
    ).json()
    assert data["gate2_pending"] is True
    assert data["severity"] is not None
    assert data["severity"]["proposed_threshold_pct"] is not None
    assert any(e.get("gate") == "gate2" for e in data["pending_events"])
    assert any(e.get("gate") == "gate2" for e in list_pending_approvals(mem))
    # Không tự ghi đè watchlist
    assert wl.get("default", "FPT").threshold_pct == before
    assert wl.upserts == []
    # Gate 1 có thể đã gửi (confidence cao) — Gate 2 vẫn pending riêng
    assert data["gate1_action"] == "sent"
    assert len(notifier.sent) == 1


def test_ac5_chat_uses_price_data_no_hitl():
    """AC: Chat API về mã watchlist → trả lời từ giá/tin, không qua HITL."""
    client, mem, _, _ = _client(latest=105.0, prev=100.0)
    resp = client.post("/chat", json={"question": "Giá FPT hiện tại?"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["hitl_used"] is False
    assert data["pending_approvals_created"] == 0
    assert data["symbol"] == "FPT"
    assert data["price"] is not None
    assert data["price"]["latest_close"] == 105.0
    assert "105" in data["answer"] or "5.00" in data["answer"] or "5%" in data["answer"]
    assert list_pending_approvals(mem) == []
    assert mem.alert_events == []


def test_ac6_guardrail_blocks_buy_sell_advice():
    """AC: Guardrail chặn lời khuyên mua/bán chắc chắn (test-plan cases)."""
    buy = check_output("A", "Nhà đầu tư nên mua FPT.", evidence=["change_pct=-4.00%"])
    sell = check_output("A", "Nhà đầu tư nên bán FPT.", evidence=["change_pct=-4.00%"])
    assert buy.ok is False and sell.ok is False

    # Câu trả lời chat / cảnh báo cuối không chứa lời khuyên (heuristic path)
    client, _, _, _ = _client(latest=105.0, prev=100.0)
    chat = client.post("/chat", json={"question": "Giá FPT?"}).json()
    assert "nên mua" not in chat["answer"].lower()
    assert "nên bán" not in chat["answer"].lower()
    assert check_output("", chat["answer"], ["change_pct=5.00%", "latest_close=105.0"]).ok

    scan = client.post("/scan", json={"symbol": "FPT", "threshold_pct": 3.0}).json()
    if scan.get("alert"):
        body = scan["alert"].get("body") or ""
        assert "nên mua" not in body.lower()
        assert "nên bán" not in body.lower()
