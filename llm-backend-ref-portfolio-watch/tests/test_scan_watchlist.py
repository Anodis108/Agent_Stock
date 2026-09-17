from __future__ import annotations

from src.portfolio_watch.application.scan_watchlist import (
    build_scan_watchlist_job,
    scan_watchlist,
)
from src.portfolio_watch.domain.entities import WatchlistItem
from src.portfolio_watch.domain.ports import PriceQuote
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


class BoomPriceSource:
    """Raise cho mã BAD; mã khác ủy quyền FakePriceSource."""

    def __init__(self, ok: FakePriceSource):
        self._ok = ok
        self.calls: list[str] = []

    def fetch_latest_close(self, symbol: str) -> PriceQuote:
        self.calls.append(symbol)
        if symbol.upper() == "BAD":
            raise RuntimeError("price boom")
        return self._ok.fetch_latest_close(symbol)


def test_scan_watchlist_continues_after_one_failure():
    wl = FakeWatchlistStore(
        [
            WatchlistItem(symbol="BAD", threshold_pct=3.0),
            WatchlistItem(symbol="FPT", threshold_pct=3.0),
            WatchlistItem(symbol="VNM", threshold_pct=5.0),
        ]
    )
    price = BoomPriceSource(
        FakePriceSource(PriceQuote("X", latest_close=101.0, prev_close=100.0))
    )
    from src.portfolio_watch.application import scan_watchlist as sw

    real_scan = sw.scan_symbol
    calls: list[str] = []

    def flaky_scan(symbol, **kwargs):
        calls.append(symbol)
        if symbol == "BAD":
            raise RuntimeError("agent crash")
        return real_scan(symbol, **kwargs)

    sw.scan_symbol = flaky_scan  # type: ignore[assignment]
    try:
        result = scan_watchlist(
            watchlist_store=wl,
            price_source=price,
            news_source=FakeNewsSource([[], [], []]),
            history_store=FakePriceHistoryStore([]),
            memory_store=FakeMemoryStore(),
            notifier=FakeNotifier(),
        )
    finally:
        sw.scan_symbol = real_scan  # type: ignore[assignment]

    assert "BAD" in calls and "FPT" in calls and "VNM" in calls
    assert result.scanned == 2
    assert result.failed == 1
    assert result.errors[0].symbol == "BAD"
    symbols_ok = {r.symbol for r in result.results}
    assert symbols_ok == {"FPT", "VNM"}


def test_price_source_error_does_not_block_other_symbols():
    """PriceSource raise ở 1 mã → agent trả error; các mã khác vẫn quét."""
    wl = FakeWatchlistStore(
        [
            WatchlistItem(symbol="BAD", threshold_pct=3.0),
            WatchlistItem(symbol="FPT", threshold_pct=3.0),
            WatchlistItem(symbol="VNM", threshold_pct=3.0),
        ]
    )
    result = scan_watchlist(
        watchlist_store=wl,
        price_source=BoomPriceSource(
            FakePriceSource(PriceQuote("X", latest_close=101.0, prev_close=100.0))
        ),
        news_source=FakeNewsSource([[] for _ in range(10)]),
        history_store=FakePriceHistoryStore([]),
        memory_store=FakeMemoryStore(),
        notifier=FakeNotifier(),
    )
    assert result.scanned == 3
    by_sym = {r.symbol: r for r in result.results}
    assert by_sym["BAD"].price is not None and by_sym["BAD"].price.error
    assert by_sym["FPT"].price is not None and by_sym["FPT"].price.error is None
    assert by_sym["VNM"].price is not None and by_sym["VNM"].price.error is None


def test_scan_watchlist_empty():
    result = scan_watchlist(
        watchlist_store=FakeWatchlistStore([]),
        price_source=FakePriceSource(PriceQuote("FPT", 100.0, 100.0)),
        news_source=FakeNewsSource([]),
        history_store=FakePriceHistoryStore([]),
        memory_store=FakeMemoryStore(),
        notifier=FakeNotifier(),
    )
    assert result.scanned == 0
    assert result.failed == 0


def test_scan_watchlist_uses_item_threshold():
    wl = FakeWatchlistStore(
        [WatchlistItem(symbol="FPT", threshold_pct=10.0)]
    )
    result = scan_watchlist(
        watchlist_store=wl,
        price_source=FakePriceSource(
            PriceQuote("FPT", latest_close=105.0, prev_close=100.0)
        ),
        news_source=FakeNewsSource([[]]),
        history_store=FakePriceHistoryStore([]),
        memory_store=FakeMemoryStore(),
        notifier=FakeNotifier(),
    )
    assert result.scanned == 1
    assert result.results[0].threshold_pct == 10.0
    assert result.results[0].gate1_action is None


def test_create_scan_scheduler_registers_interval_job():
    hits: list[int] = []

    def job():
        hits.append(1)

    sched = create_scan_scheduler(job, interval_minutes=60)
    try:
        jobs = sched.get_jobs()
        assert len(jobs) == 1
        assert jobs[0].id == "scan_watchlist"
        jobs[0].func()
        assert hits == [1]
    finally:
        stop_scan_scheduler(sched)


def test_cron_job_manual_run_isolates_symbol_errors():
    """Gọi thủ công job định kỳ (test-plan #7)."""
    wl = FakeWatchlistStore(
        [
            WatchlistItem(symbol="BAD", threshold_pct=3.0),
            WatchlistItem(symbol="FPT", threshold_pct=3.0),
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
                PriceQuote("FPT", latest_close=101.0, prev_close=100.0)
            ),
            news_source=FakeNewsSource([[], []]),
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
    assert result.scanned == 1
    assert result.failed == 1
    assert result.results[0].symbol == "FPT"


def test_scheduler_swallows_job_exception():
    def boom():
        raise RuntimeError("job dead")

    sched = create_scan_scheduler(boom, interval_minutes=60)
    try:
        assert sched.get_jobs()[0].func() is None  # không raise
    finally:
        stop_scan_scheduler(sched)


def test_invalid_interval_defaults():
    sched = create_scan_scheduler(lambda: None, interval_minutes="x")  # type: ignore[arg-type]
    try:
        assert sched.get_jobs()[0].trigger.interval.total_seconds() == 60 * 60
    finally:
        stop_scan_scheduler(sched)
