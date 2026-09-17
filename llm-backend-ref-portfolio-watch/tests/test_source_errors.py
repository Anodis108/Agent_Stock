"""Phase 5 — PriceSource/NewsSource lỗi/timeout → agent rõ, scan không crash."""

from __future__ import annotations

from fastapi.testclient import TestClient

from src.portfolio_watch.api.deps import AppDeps, set_app_deps
from src.portfolio_watch.application.scan_symbol import scan_symbol
from src.portfolio_watch.domain.agents.news_agent import HeuristicNewsBrain, run_news_agent
from src.portfolio_watch.domain.agents.price_agent import run_price_agent
from src.portfolio_watch.domain.entities import EventRoute, WatchlistItem
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


class BoomPriceSource:
    def fetch_latest_close(self, symbol: str) -> PriceQuote:
        raise TimeoutError("timeout")


class TimeoutQuotePriceSource:
    def fetch_latest_close(self, symbol: str) -> PriceQuote:
        return PriceQuote(
            symbol=symbol,
            latest_close=None,
            prev_close=None,
            error="không lấy được dữ liệu giá: timeout",
        )


class BoomNewsSource:
    def fetch_news(self, symbol, query=None, *, days=None):
        raise TimeoutError("timeout")


def test_price_agent_timeout_clear_error():
    result = run_price_agent("FPT", BoomPriceSource())
    assert result.change_pct is None
    assert result.error
    assert "không lấy được dữ liệu" in result.error


def test_news_agent_timeout_clear_error():
    result = run_news_agent("FPT", BoomNewsSource(), HeuristicNewsBrain())
    assert result.items == []
    assert result.error
    assert "không lấy được tin" in result.error


def test_scan_symbol_survives_price_and_news_timeout():
    mem = FakeMemoryStore()
    result = scan_symbol(
        "FPT",
        price_source=BoomPriceSource(),
        news_source=BoomNewsSource(),
        history_store=FakePriceHistoryStore([]),
        memory_store=mem,
        notifier=FakeNotifier(),
        watchlist_store=FakeWatchlistStore(
            [WatchlistItem(symbol="FPT", threshold_pct=3.0)]
        ),
        threshold_pct=3.0,
    )
    assert result.symbol == "FPT"
    assert result.price.error and "không lấy được dữ liệu" in result.price.error
    assert result.news.error and "không lấy được tin" in result.news.error
    assert result.routing.route == EventRoute.NORMAL
    assert result.alert is None


def test_scan_symbol_price_ok_news_timeout():
    """Chỉ NewsSource lỗi — vẫn không crash, news.error rõ."""
    result = scan_symbol(
        "FPT",
        price_source=FakePriceSource(
            PriceQuote("FPT", latest_close=101.0, prev_close=100.0)
        ),
        news_source=BoomNewsSource(),
        history_store=FakePriceHistoryStore([]),
        memory_store=FakeMemoryStore(),
        notifier=FakeNotifier(),
        threshold_pct=3.0,
    )
    assert result is not None
    assert result.price.error is None
    assert result.price.change_pct == 1.0
    assert result.news.error and "không lấy được tin" in result.news.error
    assert result.alert is None


def test_scan_symbol_price_error_quote_still_ok():
    result = scan_symbol(
        "FPT",
        price_source=TimeoutQuotePriceSource(),
        news_source=FakeNewsSource([[]]),
        history_store=FakePriceHistoryStore([]),
        memory_store=FakeMemoryStore(),
        notifier=FakeNotifier(),
        threshold_pct=3.0,
    )
    assert result.price.error and "không lấy được dữ liệu" in result.price.error
    assert result.news.error is None
    assert result.alert is None


def test_price_agent_never_returns_none_on_error():
    """test-plan: không crash, không trả None mập mờ."""
    r1 = run_price_agent("FPT", BoomPriceSource())
    r2 = run_price_agent(
        "FPT",
        FakePriceSource(
            PriceQuote("FPT", latest_close=None, prev_close=None, error="timeout")
        ),
    )
    assert r1 is not None and r1.error
    assert r2 is not None and "không lấy được dữ liệu" in (r2.error or "")


def test_post_scan_api_source_errors_return_200_with_errors():
    """API không 500 khi nguồn lỗi — body lộ price.error / news_error."""
    set_app_deps(
        AppDeps(
            price_source=BoomPriceSource(),
            news_source=BoomNewsSource(),
            history_store=FakePriceHistoryStore([]),
            memory_store=FakeMemoryStore(),
            notifier=FakeNotifier(),
            watchlist_store=FakeWatchlistStore(),
        )
    )
    try:
        client = TestClient(app)
        resp = client.post("/scan", json={"symbol": "FPT", "threshold_pct": 3})
        assert resp.status_code == 200
        data = resp.json()
        assert data["price"]["error"]
        assert "không lấy được dữ liệu" in data["price"]["error"]
        assert data["news_error"]
        assert "không lấy được tin" in data["news_error"]
        assert data["alert"] is None
    finally:
        set_app_deps(None)
