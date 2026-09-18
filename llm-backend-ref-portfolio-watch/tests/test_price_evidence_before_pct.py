"""Phase 3c — luôn có evidence giá (change_pct) trước khi so sánh %."""

from __future__ import annotations

from src.portfolio_watch.domain.agents.eval_agent import run_eval_agent
from src.portfolio_watch.domain.agents.news_agent import NewsAgentResult
from src.portfolio_watch.domain.agents.price_agent import (
    PriceAgentResult,
    has_change_pct_evidence,
    prices_have_change_pct_evidence,
)
from src.portfolio_watch.domain.entities import SeverityLevel
from tests.fakes import FakePriceHistoryStore


def test_has_change_pct_evidence():
    ok = PriceAgentResult("FPT", 100.0, 99.0, 1.01, None)
    bad = PriceAgentResult("FPT", None, None, None, "không lấy được dữ liệu giá")
    missing = PriceAgentResult("FPT", 100.0, None, None, None)
    assert has_change_pct_evidence(ok) is True
    assert has_change_pct_evidence(bad) is False
    assert has_change_pct_evidence(missing) is False
    assert has_change_pct_evidence(None) is False


def test_prices_have_change_pct_for_all_symbols():
    prices = [
        PriceAgentResult("FPT", 74.0, 73.0, 1.3, None),
        PriceAgentResult("HPG", 21.0, 20.0, 5.0, None),
    ]
    assert prices_have_change_pct_evidence(prices, ["FPT", "HPG"]) is True
    prices[1] = PriceAgentResult("HPG", None, None, None, "err")
    assert prices_have_change_pct_evidence(prices, ["FPT", "HPG"]) is False


def test_eval_without_change_pct_does_not_compare_percent():
    price = PriceAgentResult(
        symbol="FPT",
        latest_close=None,
        prev_close=None,
        change_pct=None,
        error="không lấy được dữ liệu giá",
    )
    news = NewsAgentResult(symbol="FPT", items=[], tool_calls=0)
    result = run_eval_agent(price, news, FakePriceHistoryStore([]))
    assert result.severity.level == SeverityLevel.LOW
    assert result.severity.confidence <= 0.4
    blob = " ".join(result.severity.evidence).lower()
    assert "change_pct=" not in blob or "missing" in blob or "error" in blob
    assert "thiếu" in result.severity.reasoning.lower() or "không so sánh" in (
        result.severity.reasoning.lower()
    )
