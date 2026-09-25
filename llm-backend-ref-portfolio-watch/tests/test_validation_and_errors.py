"""Unit tests kiểm tra validation và error states (Phase 7 - Item 1).

Bao phủ:
- Bắt lỗi mã cổ phiếu không tồn tại hoặc không đúng định dạng.
- Bắt lỗi dữ liệu nguồn rỗng hoặc lỗi kết nối mạng (trả về thông báo thân thiện, không crash).
- Cơ chế smart cache (TTL, hits/misses, clear) ngăn chặn rate limit từ vnstock.
- Xử lý lỗi rate limit (429 / Too Many Requests) mượt mà.
- Đảm bảo PriceAgent, AnswerComposer, ChartAgent, MarketService hoạt động an toàn trước lỗi.
"""

from __future__ import annotations

import pandas as pd
import pytest

from backend.agents.answer_composer.nodes import HeuristicAnswerDraftBrain
from backend.agents.chart_agent import run_chart_agent
from backend.agents.price_agent.nodes import run_price_agent
from backend.agents.price_agent.schemas import PriceAgentResult
from backend.domain.ports import PriceQuote
from backend.infra.market_data.price_source import VnstockPriceSource
from backend.services.market_service import MarketService


class MockQuoteFactory:
    """Mock vnstock Quote factory để kiểm thử các tình huống dữ liệu và cache."""

    def __init__(self, df: pd.DataFrame | None = None, raise_exc: Exception | None = None):
        self.df = df
        self.raise_exc = raise_exc
        self.call_count = 0
        self.history_call_count = 0

    def __call__(self, symbol: str, source: str = "VCI"):
        self.call_count += 1
        outer = self

        class _MockQuote:
            def history(self, start: str, end: str, interval: str = "1D"):
                outer.history_call_count += 1
                if outer.raise_exc is not None:
                    raise outer.raise_exc
                return outer.df

        return _MockQuote()


def test_symbol_validation_formats():
    """Kiểm tra hàm validate_symbol lọc đúng mã cổ phiếu hợp lệ và báo lỗi thân thiện khi sai."""
    source = VnstockPriceSource()

    # Hợp lệ
    sym, err = source.validate_symbol("fpt")
    assert sym == "FPT" and err is None

    sym, err = source.validate_symbol("  VNM  ")
    assert sym == "VNM" and err is None

    sym, err = source.validate_symbol("E1VFVN30")
    assert sym == "E1VFVN30" and err is None

    # Không hợp lệ
    sym, err = source.validate_symbol("")
    assert err is not None and "trống" in err.lower()

    sym, err = source.validate_symbol(None)
    assert err is not None and "trống" in err.lower()

    sym, err = source.validate_symbol("A")
    assert err is not None and "không đúng định dạng" in err.lower()

    sym, err = source.validate_symbol("!@#$%")
    assert err is not None and "không đúng định dạng" in err.lower()


def test_price_source_invalid_symbol_no_crash():
    """Khi truyền mã không hợp lệ, trả về PriceQuote có error thân thiện, không crash."""
    source = VnstockPriceSource()
    res = source.fetch_latest_close("!XYZ!")
    assert res.latest_close is None
    assert res.error is not None
    assert "không đúng định dạng" in res.error.lower()

    bars = source.fetch_history("!XYZ!")
    assert bars == []


def test_price_source_nonexistent_ticker_empty_data():
    """Khi mã không tồn tại trên sàn và vnstock trả về dataframe rỗng."""
    empty_df = pd.DataFrame()
    factory = MockQuoteFactory(df=empty_df)
    source = VnstockPriceSource(quote_factory=factory)

    quote = source.fetch_latest_close("ZZZ")
    assert quote.latest_close is None
    assert quote.error is not None
    assert "không tìm thấy dữ liệu" in quote.error.lower()
    assert "ZZZ" in quote.error

    bars = source.fetch_history("ZZZ")
    assert bars == []


def test_price_source_smart_caching_prevents_rate_limit():
    """Smart cache lưu kết quả trong bộ nhớ với TTL, ngăn chặn gọi liên tục vào vnstock."""
    sample_df = pd.DataFrame(
        {
            "time": ["2026-09-18", "2026-09-19", "2026-09-22"],
            "open": [128.0, 129.0, 130.0],
            "high": [130.0, 131.0, 132.0],
            "low": [127.0, 128.5, 129.5],
            "close": [129.0, 130.5, 131.0],
            "volume": [2000000, 2500000, 3000000],
        }
    )
    factory = MockQuoteFactory(df=sample_df)
    source = VnstockPriceSource(quote_factory=factory, cache_ttl_seconds=300.0)

    # 1. Gọi fetch_latest_close lần 1 -> Cache miss
    q1 = source.fetch_latest_close("FPT")
    assert q1.latest_close == 131.0
    assert q1.prev_close == 130.5
    assert factory.history_call_count == 1

    # 2. Gọi fetch_latest_close lần 2 và 3 -> Cache hits (không tăng call_count)
    q2 = source.fetch_latest_close("FPT")
    q3 = source.fetch_latest_close("FPT")
    assert q2.latest_close == 131.0
    assert q3.latest_close == 131.0
    assert factory.history_call_count == 1  # Vẫn chỉ gọi đúng 1 lần!

    stats = source.cache_stats()
    assert stats["hits"] == 2
    assert stats["misses"] == 1

    # 3. Gọi fetch_history lần 1 -> miss, lần 2 -> hit
    b1 = source.fetch_history("FPT", days=10)
    assert len(b1) == 3
    assert factory.history_call_count == 2

    b2 = source.fetch_history("FPT", days=10)
    assert len(b2) == 3
    assert factory.history_call_count == 2  # Hit cache!

    stats2 = source.cache_stats()
    assert stats2["hits"] == 3
    assert stats2["misses"] == 2

    # 4. Xóa cache
    source.clear_cache()
    stats3 = source.cache_stats()
    assert stats3["hits"] == 0 and stats3["misses"] == 0

    # Sau khi xóa cache, gọi lại sẽ kích hoạt fetch mới
    source.fetch_latest_close("FPT")
    assert factory.history_call_count == 3


def test_price_source_rate_limit_error_handling():
    """Khi máy chủ vnstock trả lỗi 429 Too Many Requests / Rate limit."""
    rate_limit_exc = Exception("429 Client Error: Too Many Requests for url: https://api.vnstock.com")
    factory = MockQuoteFactory(raise_exc=rate_limit_exc)
    source = VnstockPriceSource(quote_factory=factory)

    quote = source.fetch_latest_close("HPG")
    assert quote.latest_close is None
    assert quote.error is not None
    assert "rate limit" in quote.error.lower() or "giới hạn truy vấn" in quote.error.lower()
    assert "HPG" in quote.error

    bars = source.fetch_history("HPG")
    assert bars == []


def test_price_source_connection_timeout_handling():
    """Khi xảy ra lỗi timeout hoặc mất kết nối mạng."""
    timeout_exc = TimeoutError("HTTPSConnectionPool: Connection timed out")
    factory = MockQuoteFactory(raise_exc=timeout_exc)
    source = VnstockPriceSource(quote_factory=factory)

    quote = source.fetch_latest_close("VNM")
    assert quote.latest_close is None
    assert quote.error is not None
    assert "kết nối" in quote.error.lower()


def test_price_agent_handles_error_gracefully():
    """PriceAgent tiếp nhận PriceQuote lỗi và chuyển thành PriceAgentResult thân thiện."""
    empty_df = pd.DataFrame()
    factory = MockQuoteFactory(df=empty_df)
    source = VnstockPriceSource(quote_factory=factory)

    result = run_price_agent("UNKNOWN", source)
    assert isinstance(result, PriceAgentResult)
    assert result.latest_close is None
    assert result.change_pct is None
    assert result.error is not None
    assert "không tìm thấy dữ liệu giá" in result.error.lower()


def test_answer_composer_with_price_error():
    """AnswerComposer sinh phản hồi thân thiện khi PriceAgent báo lỗi, không crash."""
    brain = HeuristicAnswerDraftBrain()
    price_err = PriceAgentResult(
        symbol="ABC",
        latest_close=None,
        prev_close=None,
        change_pct=None,
        error="Không tìm thấy dữ liệu giá cho mã 'ABC'. Vui lòng kiểm tra lại mã cổ phiếu.",
    )
    ans = brain.compose(
        question="Giá ABC thế nào?",
        symbol="ABC",
        price=price_err,
        news=None,
        eval_result=None,
        evidence=[],
        model="heuristic",
        attempt=0,
        previous_violations=[],
    )
    assert isinstance(ans, str)
    assert "ABC" in ans
    assert "Không tìm thấy dữ liệu giá" in ans
    assert "không phải lời khuyên đầu tư" in ans


def test_chart_agent_empty_bars_graceful():
    """ChartAgent khi không có dữ liệu giá trả về ChartResult(success=False), không crash."""
    res = run_chart_agent("EMPTY", [])
    assert res.success is False
    assert res.error is not None
    assert "Không có dữ liệu giá" in res.error


def test_market_service_safe_on_unknown_symbol():
    """MarketService xử lý an toàn khi truy vấn mã không có dữ liệu."""
    empty_df = pd.DataFrame()
    factory = MockQuoteFactory(df=empty_df)
    source = VnstockPriceSource(quote_factory=factory)

    # Chế độ fallback=False trả về rỗng không crash
    service = MarketService(price_source=source)
    records = service.sync_symbol_history("NONEXISTENT", days=10, fallback_on_empty=False)
    assert records == []

    # Chế độ fallback=True sinh dữ liệu giả định để app tiếp tục chạy không crash
    fallback_records = service.sync_symbol_history("FALLBACK_SYM", days=10, fallback_on_empty=True)
    assert len(fallback_records) == 10
