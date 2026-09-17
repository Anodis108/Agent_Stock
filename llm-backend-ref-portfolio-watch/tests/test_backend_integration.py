"""Integration backend theo specs/test-plan.md (chưa cần API/UI).

Map e2e 1–7 bằng application layer + fake ports (không HTTP).
"""

from __future__ import annotations

from src.portfolio_watch.application.answer_question import answer_question
from src.portfolio_watch.application.review_approval import (
    approve_pending,
    list_pending_approvals,
    reject_pending,
)
from src.portfolio_watch.application.scan_symbol import scan_symbol
from src.portfolio_watch.application.scan_watchlist import (
    build_scan_watchlist_job,
    scan_watchlist,
)
from src.portfolio_watch.domain.agents.news_agent import HeuristicNewsBrain
from src.portfolio_watch.domain.entities import (
    AlertStatus,
    EventRoute,
    Severity,
    SeverityLevel,
    WatchlistItem,
)
from src.portfolio_watch.domain.ports import NewsItem, PriceQuote
from src.portfolio_watch.infra.scheduler.cron import (
    create_scan_scheduler,
    stop_scan_scheduler,
)
from tests.fakes import (
    FakeMemoryStore,
    FakeNewsSource,
    FakeNotifier,
    FakePriceHistoryStore,
    FakePriceSource,
    FakeWatchlistStore,
)


def _scan_deps(
    *,
    latest: float,
    prev: float,
    news: list[NewsItem] | None = None,
    mem: FakeMemoryStore | None = None,
    notifier: FakeNotifier | None = None,
):
    return {
        "price_source": FakePriceSource(
            PriceQuote("FPT", latest_close=latest, prev_close=prev)
        ),
        "news_source": FakeNewsSource([news or []]),
        "history_store": FakePriceHistoryStore([]),
        "memory_store": mem or FakeMemoryStore(),
        "notifier": notifier or FakeNotifier(),
        "news_brain": HeuristicNewsBrain(),
    }


def test_it1_scan_normal_no_alert():
    """test-plan #1: quét mã bình thường → không alert."""
    deps = _scan_deps(latest=101.0, prev=100.0)
    result = scan_symbol("FPT", threshold_pct=3.0, **deps)
    assert result.routing.route == EventRoute.NORMAL
    assert result.alert is None
    assert result.gate1_action is None
    assert result.gate2_pending is False
    assert deps["notifier"].sent == []
    assert list_pending_approvals(deps["memory_store"]) == []
    assert deps["memory_store"].alert_events == []


def test_it2_scan_abnormal_high_confidence_auto_send():
    """test-plan #2: bất thường + confidence cao → gửi, không bản ghi chờ duyệt."""
    deps = _scan_deps(latest=105.0, prev=100.0)
    result = scan_symbol("FPT", threshold_pct=3.0, **deps)
    assert result.routing.route == EventRoute.ABNORMAL
    assert result.gate1_action == "sent"
    assert result.alert is not None
    assert result.alert.status == AlertStatus.SENT
    assert len(deps["notifier"].sent) == 1
    assert result.gate2_pending is False
    # Không có Gate 1 / Gate 2 chờ duyệt
    assert list_pending_approvals(deps["memory_store"]) == []


def test_it3_scan_low_confidence_approve_then_reject_paths():
    """test-plan #3: confidence thấp → pending; approve gửi; reject không gửi."""

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

    # approve path
    mem_a = FakeMemoryStore()
    n_a = FakeNotifier()
    deps_a = _scan_deps(latest=105.0, prev=100.0, mem=mem_a, notifier=n_a)
    r_a = scan_symbol(
        "FPT", threshold_pct=3.0, eval_brain=LowConfEval(), **deps_a
    )
    assert r_a.gate1_action == "pending_approval"
    assert n_a.sent == []
    pending = list_pending_approvals(mem_a)
    assert len(pending) == 1 and pending[0]["gate"] == "gate1"
    assert pending[0].get("alert") is not None  # đúng nội dung chờ duyệt
    aid = pending[0]["approval_id"]
    approved = approve_pending(
        aid,
        memory_store=mem_a,
        notifier=n_a,
        watchlist_store=FakeWatchlistStore(),
    )
    assert approved.ok is True
    assert len(n_a.sent) == 1
    assert n_a.sent[0].status == AlertStatus.SENT
    assert list_pending_approvals(mem_a) == []

    # reject path
    mem_r = FakeMemoryStore()
    n_r = FakeNotifier()
    deps_r = _scan_deps(latest=105.0, prev=100.0, mem=mem_r, notifier=n_r)
    r_r = scan_symbol(
        "FPT", threshold_pct=3.0, eval_brain=LowConfEval(), **deps_r
    )
    pid = list_pending_approvals(mem_r)[0]["approval_id"]
    rejected = reject_pending(
        pid, "tin nhiễu", memory_store=mem_r, watchlist_store=FakeWatchlistStore()
    )
    assert rejected.ok is True
    assert n_r.sent == []
    assert mem_r.rejections[0]["reason"] == "tin nhiễu"
    assert mem_r.rejections[0]["gate"] == "gate1"
    assert list_pending_approvals(mem_r) == []


def test_it4_gate2_pending_even_high_confidence():
    """test-plan #4: đề xuất ngưỡng → luôn Gate 2 pending; không tự áp dụng."""
    wl = FakeWatchlistStore(
        [WatchlistItem(symbol="FPT", threshold_pct=3.0, user_id="default")]
    )
    deps = _scan_deps(latest=108.0, prev=100.0)
    result = scan_symbol(
        "FPT", threshold_pct=3.0, watchlist_store=wl, **deps
    )
    assert result.gate1_action == "sent"
    assert result.gate2_pending is True
    assert result.severity is not None
    assert result.severity.proposed_threshold_pct is not None
    pending = list_pending_approvals(deps["memory_store"])
    assert any(e.get("gate") == "gate2" for e in pending)
    # Không tự động ghi đè watchlist
    assert wl.get("default", "FPT").threshold_pct == 3.0
    assert wl.upserts == []


def test_it5_chat_price_no_hitl():
    """test-plan #5: hỏi giá → trả lời, không pending HITL."""
    mem = FakeMemoryStore()
    result = answer_question(
        "Giá FPT hiện tại?",
        price_source=FakePriceSource(
            PriceQuote("FPT", latest_close=105.0, prev_close=100.0)
        ),
        news_source=FakeNewsSource([[]]),
        history_store=FakePriceHistoryStore([]),
        memory_store=mem,
        news_brain=HeuristicNewsBrain(),
    )
    assert result.hitl_used is False
    assert result.pending_approvals_created == 0
    assert result.eval_result is None
    assert result.price is not None and result.price.change_pct == 5.0
    assert "105" in result.answer or "5.00" in result.answer
    assert list_pending_approvals(mem) == []
    assert mem.alert_events == []


def test_it6_chat_explain_mentions_news():
    """test-plan #6: hỏi tại sao giảm → có tin/lý do cụ thể; không HITL."""
    mem = FakeMemoryStore()
    news = [NewsItem(title="FPT giảm do tin xấu", snippet="giảm", symbol="FPT")]
    result = answer_question(
        "Tại sao giá FPT giảm?",
        price_source=FakePriceSource(
            PriceQuote("FPT", latest_close=95.0, prev_close=100.0)
        ),
        news_source=FakeNewsSource([news]),
        history_store=FakePriceHistoryStore([]),
        memory_store=mem,
        news_brain=HeuristicNewsBrain(),
    )
    assert "eval" in result.routing.agents_to_call
    assert result.eval_result is not None
    assert result.news and any("FPT" in i.title for i in result.news.items)
    assert "tin" in result.answer.lower() or "giảm" in result.answer.lower()
    assert result.hitl_used is False
    assert result.pending_approvals_created == 0
    assert list_pending_approvals(mem) == []
    assert mem.alert_events == []


def test_it7_cron_manual_multi_symbol_isolation():
    """test-plan #7: cron thủ công, 1 mã lỗi không chặn mã khác."""
    wl = FakeWatchlistStore(
        [
            WatchlistItem(symbol="BAD", threshold_pct=3.0),
            WatchlistItem(symbol="FPT", threshold_pct=3.0),
            WatchlistItem(symbol="VNM", threshold_pct=3.0),
        ]
    )
    from src.portfolio_watch.application import scan_watchlist as sw

    real = sw.scan_symbol

    def flaky(symbol, **kwargs):
        if symbol == "BAD":
            raise RuntimeError("boom")
        return real(symbol, **kwargs)

    sw.scan_symbol = flaky  # type: ignore[assignment]
    try:
        job = build_scan_watchlist_job(
            watchlist_store=wl,
            price_source=FakePriceSource(
                PriceQuote("X", latest_close=101.0, prev_close=100.0)
            ),
            news_source=FakeNewsSource([[] for _ in range(10)]),
            history_store=FakePriceHistoryStore([]),
            memory_store=FakeMemoryStore(),
            notifier=FakeNotifier(),
        )
        sched = create_scan_scheduler(job, interval_minutes=60)
        try:
            result = sched.get_jobs()[0].func()
        finally:
            stop_scan_scheduler(sched)
    finally:
        sw.scan_symbol = real  # type: ignore[assignment]

    assert result is not None
    assert result.scanned == 2
    assert result.failed == 1
    assert {r.symbol for r in result.results} == {"FPT", "VNM"}


def test_it_scan_watchlist_direct_also_isolates():
    """Bổ sung: scan_watchlist trực tiếp (không qua scheduler)."""
    wl = FakeWatchlistStore(
        [
            WatchlistItem(symbol="BAD", threshold_pct=3.0),
            WatchlistItem(symbol="FPT", threshold_pct=3.0),
        ]
    )
    from src.portfolio_watch.application import scan_watchlist as sw

    real = sw.scan_symbol
    sw.scan_symbol = (  # type: ignore[assignment]
        lambda s, **k: (_ for _ in ()).throw(RuntimeError("x"))
        if s == "BAD"
        else real(s, **k)
    )
    try:
        result = scan_watchlist(
            watchlist_store=wl,
            price_source=FakePriceSource(
                PriceQuote("FPT", latest_close=101.0, prev_close=100.0)
            ),
            news_source=FakeNewsSource([[], []]),
            history_store=FakePriceHistoryStore([]),
            memory_store=FakeMemoryStore(),
            notifier=FakeNotifier(),
        )
    finally:
        sw.scan_symbol = real  # type: ignore[assignment]

    assert result.scanned == 1
    assert result.results[0].symbol == "FPT"
    assert result.errors[0].symbol == "BAD"
