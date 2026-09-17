"""Phase 5 — xác nhận tích hợp: cron/watchlist, 1 mã lỗi không chặn mã khác.

test-plan #7 + implementation-plan Phase 5.
"""

from __future__ import annotations

from src.portfolio_watch.application.scan_watchlist import (
    build_scan_watchlist_job,
    scan_watchlist,
)
from src.portfolio_watch.domain.entities import WatchlistItem
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


class SelectiveBoomPrice:
    """Chỉ mã BAD raise; mã khác trả quote ổn."""

    def __init__(self):
        self.calls: list[str] = []
        self._ok = FakePriceSource(
            PriceQuote("X", latest_close=101.0, prev_close=100.0)
        )

    def fetch_latest_close(self, symbol: str) -> PriceQuote:
        self.calls.append(symbol)
        if symbol.upper() == "BAD":
            raise TimeoutError("timeout")
        return self._ok.fetch_latest_close(symbol)


class SelectiveBoomNews:
    def __init__(self):
        self.calls: list[str] = []

    def fetch_news(self, symbol, query=None, *, days=None):
        self.calls.append(symbol)
        if symbol.upper() == "BAD":
            raise TimeoutError("timeout")
        return [NewsItem(title=f"{symbol} tin", snippet=symbol, symbol=symbol)]


def _watchlist_three() -> FakeWatchlistStore:
    return FakeWatchlistStore(
        [
            WatchlistItem(symbol="FPT", threshold_pct=3.0),
            WatchlistItem(symbol="BAD", threshold_pct=3.0),
            WatchlistItem(symbol="VNM", threshold_pct=3.0),
        ]
    )


def test_integration_agent_crash_middle_symbol_others_ok():
    """Agent crash ở mã giữa — FPT + VNM vẫn có kết quả."""
    wl = _watchlist_three()
    from src.portfolio_watch.application import scan_watchlist as sw

    real = sw.scan_symbol
    order: list[str] = []

    def flaky(symbol, **kwargs):
        order.append(symbol)
        if symbol == "BAD":
            raise RuntimeError("agent crash")
        return real(symbol, **kwargs)

    sw.scan_symbol = flaky  # type: ignore[assignment]
    try:
        result = scan_watchlist(
            watchlist_store=wl,
            price_source=FakePriceSource(
                PriceQuote("X", latest_close=101.0, prev_close=100.0)
            ),
            news_source=FakeNewsSource([[] for _ in range(10)]),
            history_store=FakePriceHistoryStore([]),
            memory_store=FakeMemoryStore(),
            notifier=FakeNotifier(),
        )
    finally:
        sw.scan_symbol = real  # type: ignore[assignment]

    assert order == ["FPT", "BAD", "VNM"]
    assert result.scanned == 2
    assert result.failed == 1
    assert {r.symbol for r in result.results} == {"FPT", "VNM"}
    assert result.errors[0].symbol == "BAD"


def test_integration_price_timeout_one_symbol_others_scanned():
    """PriceSource timeout 1 mã — agent error; các mã khác vẫn scanned."""
    result = scan_watchlist(
        watchlist_store=_watchlist_three(),
        price_source=SelectiveBoomPrice(),
        news_source=FakeNewsSource([[] for _ in range(10)]),
        history_store=FakePriceHistoryStore([]),
        memory_store=FakeMemoryStore(),
        notifier=FakeNotifier(),
    )
    assert result.scanned == 3
    by = {r.symbol: r for r in result.results}
    assert by["BAD"].price.error and "không lấy được dữ liệu" in by["BAD"].price.error
    assert by["FPT"].price.error is None and by["FPT"].price.change_pct is not None
    assert by["VNM"].price.error is None and by["VNM"].price.change_pct is not None


def test_integration_news_timeout_one_symbol_others_scanned():
    """NewsSource timeout 1 mã — không chặn FPT/VNM."""
    result = scan_watchlist(
        watchlist_store=_watchlist_three(),
        price_source=FakePriceSource(
            PriceQuote("X", latest_close=101.0, prev_close=100.0)
        ),
        news_source=SelectiveBoomNews(),
        history_store=FakePriceHistoryStore([]),
        memory_store=FakeMemoryStore(),
        notifier=FakeNotifier(),
    )
    assert result.scanned == 3
    by = {r.symbol: r for r in result.results}
    assert by["BAD"].news.error and "không lấy được tin" in by["BAD"].news.error
    assert by["FPT"].news.error is None
    assert by["VNM"].news.error is None
    # FPT/VNM vẫn có tin (luồng độc lập)
    assert any("FPT" in (i.title or "") for i in by["FPT"].news.items)
    assert any("VNM" in (i.title or "") for i in by["VNM"].news.items)


def test_integration_agent_crash_first_and_last_still_isolates():
    """Lỗi mã đầu / mã cuối — các mã còn lại vẫn chạy (độc lập)."""
    from src.portfolio_watch.application import scan_watchlist as sw

    real = sw.scan_symbol

    def run_with_bad(bad_sym: str, symbols: list[str]):
        wl = FakeWatchlistStore(
            [WatchlistItem(symbol=s, threshold_pct=3.0) for s in symbols]
        )
        order: list[str] = []

        def flaky(symbol, **kwargs):
            order.append(symbol)
            if symbol == bad_sym:
                raise RuntimeError("boom")
            return real(symbol, **kwargs)

        sw.scan_symbol = flaky  # type: ignore[assignment]
        try:
            return (
                scan_watchlist(
                    watchlist_store=wl,
                    price_source=FakePriceSource(
                        PriceQuote("X", latest_close=101.0, prev_close=100.0)
                    ),
                    news_source=FakeNewsSource([[] for _ in range(10)]),
                    history_store=FakePriceHistoryStore([]),
                    memory_store=FakeMemoryStore(),
                    notifier=FakeNotifier(),
                ),
                order,
            )
        finally:
            sw.scan_symbol = real  # type: ignore[assignment]

    # BAD đầu
    r1, o1 = run_with_bad("BAD", ["BAD", "FPT", "VNM"])
    assert o1 == ["BAD", "FPT", "VNM"]
    assert {r.symbol for r in r1.results} == {"FPT", "VNM"}
    assert r1.errors[0].symbol == "BAD"

    # BAD cuối
    r2, o2 = run_with_bad("BAD", ["FPT", "VNM", "BAD"])
    assert o2 == ["FPT", "VNM", "BAD"]
    assert {r.symbol for r in r2.results} == {"FPT", "VNM"}
    assert r2.errors[0].symbol == "BAD"


def test_integration_cron_job_path_isolates_failure():
    """APScheduler job thủ công (build_scan_watchlist_job) — isolation, không raise."""
    wl = _watchlist_three()
    from src.portfolio_watch.application import scan_watchlist as sw

    real = sw.scan_symbol
    order: list[str] = []

    def flaky(symbol, **kwargs):
        order.append(symbol)
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
            # cùng path cron: _safe_job → build_scan_watchlist_job — không raise
            result = sched.get_jobs()[0].func()
        finally:
            stop_scan_scheduler(sched)
    finally:
        sw.scan_symbol = real  # type: ignore[assignment]

    assert result is not None
    assert order == ["FPT", "BAD", "VNM"]
    assert result.scanned == 2
    assert result.failed == 1
    assert {r.symbol for r in result.results} == {"FPT", "VNM"}
    assert result.errors[0].symbol == "BAD"
    # mỗi mã thành công có luồng giám sát (có price)
    for r in result.results:
        assert r.price is not None
        assert r.news is not None
