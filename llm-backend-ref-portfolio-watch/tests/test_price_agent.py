from __future__ import annotations

from src.portfolio_watch.domain.agents.price_agent import run_price_agent
from src.portfolio_watch.domain.ports import PriceQuote
from tests.fakes import FakePriceSource


def test_price_up():
    src = FakePriceSource(PriceQuote("FPT", latest_close=110.0, prev_close=100.0))
    result = run_price_agent("FPT", src)
    assert result.error is None
    assert result.change_pct == 10.0


def test_price_down():
    src = FakePriceSource(PriceQuote("FPT", latest_close=90.0, prev_close=100.0))
    result = run_price_agent("FPT", src)
    assert result.error is None
    assert result.change_pct == -10.0


def test_price_flat():
    src = FakePriceSource(PriceQuote("FPT", latest_close=100.0, prev_close=100.0))
    result = run_price_agent("FPT", src)
    assert result.error is None
    assert result.change_pct == 0.0


def test_price_source_error():
    src = FakePriceSource(
        PriceQuote("FPT", latest_close=None, prev_close=None, error="timeout")
    )
    result = run_price_agent("FPT", src)
    assert result is not None
    assert result.change_pct is None
    assert result.error
    assert "không lấy được dữ liệu" in result.error
    assert "timeout" in result.error


def test_price_missing_data():
    src = FakePriceSource(PriceQuote("FPT", latest_close=None, prev_close=100.0))
    result = run_price_agent("FPT", src)
    assert result.change_pct is None
    assert result.error is not None
    assert "không lấy được dữ liệu" in result.error


def test_price_missing_prev_close():
    src = FakePriceSource(PriceQuote("FPT", latest_close=100.0, prev_close=None))
    result = run_price_agent("FPT", src)
    assert result is not None
    assert result.change_pct is None
    assert result.error is not None


def test_price_source_raises():
    class Boom:
        def fetch_latest_close(self, symbol: str) -> PriceQuote:
            raise RuntimeError("network down")

    result = run_price_agent("FPT", Boom())
    assert result is not None
    assert result.change_pct is None
    assert "không lấy được dữ liệu" in (result.error or "")
