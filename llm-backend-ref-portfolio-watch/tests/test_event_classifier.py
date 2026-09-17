from __future__ import annotations

from src.portfolio_watch.domain.agents.event_classifier import classify_event
from src.portfolio_watch.domain.agents.news_agent import NewsAgentResult
from src.portfolio_watch.domain.agents.price_agent import PriceAgentResult
from src.portfolio_watch.domain.entities import EventRoute
from src.portfolio_watch.domain.ports import NewsItem


def _price(change_pct: float | None) -> PriceAgentResult:
    return PriceAgentResult(
        symbol="FPT",
        latest_close=100.0,
        prev_close=100.0,
        change_pct=change_pct,
    )


def _news(*titles: str) -> NewsAgentResult:
    items = [NewsItem(title=t, snippet=t) for t in titles]
    return NewsAgentResult(symbol="FPT", items=items, tool_calls=1)


def test_small_move_no_bad_news_is_normal():
    decision = classify_event(_price(0.5), _news("FPT giữ vững đà tăng nhẹ"))
    assert decision.route == EventRoute.NORMAL


def test_large_move_down_is_abnormal():
    decision = classify_event(_price(-5.0), _news(), threshold_pct=3.0)
    assert decision.route == EventRoute.ABNORMAL
    assert "change_pct" in decision.reason


def test_large_move_up_is_abnormal():
    decision = classify_event(_price(5.0), _news(), threshold_pct=3.0)
    assert decision.route == EventRoute.ABNORMAL


def test_negative_news_is_abnormal_even_if_price_flat():
    decision = classify_event(
        _price(0.2),
        _news("FPT bị phạt hành chính", "Thị trường chung ổn định"),
        threshold_pct=3.0,
    )
    assert decision.route == EventRoute.ABNORMAL
    assert "tin tiêu cực" in decision.reason


def test_negated_keyword_stays_normal():
    decision = classify_event(
        _price(0.3),
        _news("FPT khẳng định không giảm kế hoạch đầu tư"),
        threshold_pct=3.0,
    )
    assert decision.route == EventRoute.NORMAL


def test_dam_bao_not_false_positive_from_am():
    decision = classify_event(
        _price(0.1),
        _news("FPT đảm bảo tiến độ dự án"),
        threshold_pct=3.0,
    )
    assert decision.route == EventRoute.NORMAL


def test_brain_error_does_not_escalate():
    class Boom:
        def classify(self, price, news, threshold_pct):
            raise RuntimeError("llm down")

    decision = classify_event(_price(-9.0), _news(), brain=Boom())
    assert decision.route == EventRoute.NORMAL
    assert "classifier lỗi" in decision.reason
