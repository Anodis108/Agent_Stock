from __future__ import annotations

from src.portfolio_watch.domain.agents.news_agent import (
    HeuristicNewsBrain,
    NewsReactAction,
    run_news_agent,
)
from src.portfolio_watch.domain.ports import NewsItem
from tests.fakes import FakeNewsSource


def test_filters_out_unrelated_news():
    src = FakeNewsSource(
        [
            [
                NewsItem(title="Thị trường chung tăng điểm", snippet="VN-Index"),
                NewsItem(title="Giá vàng thế giới", snippet="USD"),
            ]
        ]
    )
    brain = HeuristicNewsBrain(min_relevant=1, queries=["FPT"])
    result = run_news_agent("FPT", src, brain, max_steps=3)
    assert result.error is None
    assert result.items == []
    assert result.tool_calls == 1


def test_react_loop_calls_tool_twice_then_stops():
    """Lần 1 tin rác → chưa đủ; lần 2 có tin FPT → finish (không lặp vô hạn)."""
    src = FakeNewsSource(
        [
            [NewsItem(title="Tin vĩ mô", snippet="lạm phát")],
            [
                NewsItem(title="FPT công bố kết quả quý", snippet="FPT lãi tăng"),
                NewsItem(title="Unrelated bank news", snippet="VCB"),
            ],
            [NewsItem(title="should not be fetched", snippet="FPT")],
        ]
    )
    brain = HeuristicNewsBrain(min_relevant=1, queries=["macro", "FPT kết quả"])
    result = run_news_agent("FPT", src, brain, max_steps=5)
    assert result.error is None
    assert result.tool_calls == 2
    assert len(src.calls) == 2
    assert len(result.items) == 1
    assert "FPT" in result.items[0].title.upper()


def test_max_steps_caps_infinite_loop():
    class AlwaysSearch:
        def decide(self, symbol, gathered, step):
            return NewsReactAction(kind="search", query=f"q{step}")

        def filter_relevant(self, symbol, items):
            return items

    src = FakeNewsSource([[NewsItem(title="x", snippet="y")] for _ in range(10)])
    result = run_news_agent("FPT", src, AlwaysSearch(), max_steps=3)
    assert result.tool_calls == 3
    assert len(src.calls) == 3


def test_fetch_error_keeps_prior_relevant_items():
    class BoomAfterFirst(FakeNewsSource):
        def fetch_news(self, symbol, query=None, *, days=None):
            self.calls.append((symbol, query, days))
            if len(self.calls) == 1:
                return [NewsItem(title="FPT tin 1", snippet="FPT")]
            raise RuntimeError("cafef down")

    src = BoomAfterFirst([])
    brain = HeuristicNewsBrain(min_relevant=99, queries=["a", "b"])
    result = run_news_agent("FPT", src, brain, max_steps=5)
    assert result.tool_calls == 2
    assert len(result.items) == 1
    assert result.error is not None
    assert "không lấy được tin" in result.error
