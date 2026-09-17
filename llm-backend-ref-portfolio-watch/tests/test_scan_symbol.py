from __future__ import annotations

from src.portfolio_watch.application.scan_symbol import scan_symbol, should_auto_send
from src.portfolio_watch.domain.agents.news_agent import HeuristicNewsBrain
from src.portfolio_watch.domain.agents.price_agent import PriceAgentResult
from src.portfolio_watch.domain.entities import (
    AlertStatus,
    EventRoute,
    RoutingDecision,
    Severity,
    SeverityLevel,
    WatchlistItem,
)
from src.portfolio_watch.domain.ports import NewsItem, PriceQuote
from tests.fakes import (
    FakeMemoryStore,
    FakeNewsSource,
    FakeNotifier,
    FakePriceHistoryStore,
    FakePriceSource,
    FakeWatchlistStore,
)


def _deps(
    *,
    latest: float,
    prev: float,
    news: list[NewsItem] | None = None,
):
    return {
        "price_source": FakePriceSource(
            PriceQuote("FPT", latest_close=latest, prev_close=prev)
        ),
        "news_source": FakeNewsSource([news or []]),
        "history_store": FakePriceHistoryStore([]),
        "memory_store": FakeMemoryStore(),
        "notifier": FakeNotifier(),
        "news_brain": HeuristicNewsBrain(),
    }


def test_scan_normal_no_alert():
    deps = _deps(latest=101.0, prev=100.0)  # +1% < 3%
    result = scan_symbol("FPT", threshold_pct=3.0, **deps)
    assert result.routing.route == EventRoute.NORMAL
    assert result.alert is None
    assert result.gate1_action is None
    assert deps["notifier"].sent == []
    assert deps["memory_store"].alert_events == []


def test_scan_abnormal_high_confidence_auto_send():
    # +5% >= 3%, heuristic eval confidence ~0.8 → auto-send, no Gate2
    deps = _deps(latest=105.0, prev=100.0)
    result = scan_symbol("FPT", threshold_pct=3.0, **deps)
    assert result.routing.route == EventRoute.ABNORMAL
    assert result.gate1_action == "sent"
    assert result.alert is not None
    assert result.alert.status == AlertStatus.SENT
    assert len(deps["notifier"].sent) == 1
    assert not result.gate2_pending
    # Confidence Gate: không tạo bản ghi chờ duyệt Gate 1
    assert not any(
        e.get("gate") == "gate1" for _, e in deps["memory_store"].alert_events
    )


def test_scan_uses_watchlist_threshold():
    """Ngưỡng từ watchlist: +5% < 10% → bình thường, không alert."""
    deps = _deps(latest=105.0, prev=100.0)
    wl = FakeWatchlistStore(
        [WatchlistItem(symbol="FPT", threshold_pct=10.0, user_id="default")]
    )
    result = scan_symbol("FPT", watchlist_store=wl, **deps)
    assert result.threshold_pct == 10.0
    assert result.routing.route == EventRoute.NORMAL
    assert result.alert is None
    assert wl.upserts == []


def test_scan_gate2_never_auto_applies_watchlist():
    deps = _deps(latest=108.0, prev=100.0)
    wl = FakeWatchlistStore(
        [WatchlistItem(symbol="FPT", threshold_pct=3.0, user_id="default")]
    )
    result = scan_symbol("FPT", watchlist_store=wl, **deps)
    assert result.gate2_pending is True
    assert wl.upserts == []
    assert wl.get("default", "FPT").threshold_pct == 3.0


def test_scan_notifier_failure_falls_back_to_gate1():
    class BoomNotifier:
        def send(self, alert):
            raise RuntimeError("notify down")

    deps = _deps(latest=105.0, prev=100.0)
    deps["notifier"] = BoomNotifier()
    result = scan_symbol("FPT", threshold_pct=3.0, **deps)
    assert result.gate1_action == "pending_approval"
    assert result.alert is not None
    assert result.alert.status == AlertStatus.PENDING_APPROVAL
    assert result.error and "chuyển chờ duyệt" in result.error
    assert any(
        e.get("gate") == "gate1"
        for e in deps["memory_store"].list_alert_events("default")
    )


def test_scan_abnormal_low_confidence_gate1_pending():
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

    deps = _deps(latest=105.0, prev=100.0)
    result = scan_symbol(
        "FPT", threshold_pct=3.0, eval_brain=LowConfEval(), **deps
    )
    assert result.gate1_action == "pending_approval"
    assert result.alert is not None
    assert result.alert.status == AlertStatus.PENDING_APPROVAL
    assert deps["notifier"].sent == []
    events = deps["memory_store"].list_alert_events("default")
    assert any(e.get("gate") == "gate1" for e in events)


def test_scan_gate2_always_pending_even_high_confidence():
    # +8% → proposed_threshold + auto-send
    deps = _deps(latest=108.0, prev=100.0)
    result = scan_symbol("FPT", threshold_pct=3.0, **deps)
    assert result.gate1_action == "sent"
    assert result.gate2_pending is True
    events = deps["memory_store"].list_alert_events("default")
    assert any(e.get("gate") == "gate2" for e in events)
    assert result.severity is not None
    assert result.severity.proposed_threshold_pct is not None


def test_scan_high_confidence_but_below_threshold_goes_gate1():
    """Tin tiêu cực → abnormal; |change| < ngưỡng → không auto-send."""

    class ForceAbnormal:
        def classify(self, price, news, threshold_pct):
            return RoutingDecision(
                route=EventRoute.ABNORMAL, reason="tin tiêu cực ép"
            )

    class HighConfEval:
        def needs_history(self, price, news, history):
            return False

        def build_severity(self, price, news, history):
            return Severity(
                level=SeverityLevel.HIGH,
                confidence=0.95,
                reasoning="tin xấu",
                evidence=["news:FPT bị phạt"],
            )

    news = [NewsItem(title="FPT bị phạt", snippet="phạt", symbol="FPT")]
    deps = _deps(latest=101.0, prev=100.0, news=news)  # +1% < 3%
    result = scan_symbol(
        "FPT",
        threshold_pct=3.0,
        classifier_brain=ForceAbnormal(),
        eval_brain=HighConfEval(),
        **deps,
    )
    assert result.gate1_action == "pending_approval"
    assert deps["notifier"].sent == []


def test_should_auto_send_formula():
    sev = Severity(
        level=SeverityLevel.HIGH,
        confidence=0.9,
        reasoning="x",
        evidence=["e"],
    )
    price_ok = PriceAgentResult("FPT", 105.0, 100.0, 5.0)
    price_low = PriceAgentResult("FPT", 101.0, 100.0, 1.0)
    assert should_auto_send(sev, price_ok, 3.0) is True
    assert should_auto_send(sev, price_low, 3.0) is False
    sev_low = sev.model_copy(update={"confidence": 0.5})
    assert should_auto_send(sev_low, price_ok, 3.0) is False


def test_scan_empty_symbol():
    deps = _deps(latest=100.0, prev=100.0)
    result = scan_symbol("  ", **deps)
    assert result.error == "symbol rỗng"
    assert deps["notifier"].sent == []
