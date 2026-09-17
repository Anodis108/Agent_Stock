from __future__ import annotations

from src.portfolio_watch.domain.agents.eval_agent import run_eval_agent
from src.portfolio_watch.domain.agents.news_agent import NewsAgentResult
from src.portfolio_watch.domain.agents.price_agent import PriceAgentResult
from src.portfolio_watch.domain.ports import NewsItem, PriceBar
from tests.fakes import FakePriceHistoryStore


def test_clear_data_skips_price_history():
    price = PriceAgentResult(
        symbol="FPT",
        latest_close=90.0,
        prev_close=100.0,
        change_pct=-10.0,
    )
    news = NewsAgentResult(
        symbol="FPT",
        items=[NewsItem(title="FPT giảm mạnh sau tin xấu", snippet="FPT")],
        tool_calls=1,
    )
    store = FakePriceHistoryStore(
        [PriceBar(date="2026-01-01", close=100.0), PriceBar(date="2026-01-10", close=90.0)]
    )
    result = run_eval_agent(price, news, store)
    assert result.history_calls == 0
    assert store.calls == []
    assert result.severity.confidence >= 0.8
    assert result.severity.evidence


def test_ambiguous_calls_history_and_lowers_confidence_when_unsupported():
    """|%| nhỏ + không tin → gọi history; lịch sử ngược chiều → confidence thấp hơn."""
    price = PriceAgentResult(
        symbol="FPT",
        latest_close=98.0,
        prev_close=100.0,
        change_pct=-2.0,
    )
    news = NewsAgentResult(symbol="FPT", items=[], tool_calls=0)
    store_oppose = FakePriceHistoryStore(
        [
            PriceBar(date="2026-01-01", close=80.0),
            PriceBar(date="2026-01-15", close=100.0),
        ]
    )
    store_support = FakePriceHistoryStore(
        [
            PriceBar(date="2026-01-01", close=110.0),
            PriceBar(date="2026-01-15", close=98.0),
        ]
    )
    opposed = run_eval_agent(price, news, store_oppose)
    supported = run_eval_agent(price, news, store_support)
    assert opposed.history_calls == 1
    assert supported.history_calls == 1
    assert opposed.severity.confidence < supported.severity.confidence
    assert opposed.severity.confidence <= 0.45
    assert "không ủng hộ" in opposed.severity.reasoning


def test_history_store_error_still_returns_severity():
    class BoomStore:
        def read_history(self, symbol: str, days: int = 30):
            raise RuntimeError("db down")

    price = PriceAgentResult(
        symbol="FPT", latest_close=98.0, prev_close=100.0, change_pct=-1.0
    )
    news = NewsAgentResult(symbol="FPT", items=[], tool_calls=0)
    result = run_eval_agent(price, news, BoomStore())
    assert result.history_calls == 1
    assert result.severity.confidence <= 0.35
    assert "Lỗi đọc lịch sử" in result.severity.reasoning
