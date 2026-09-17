from __future__ import annotations

import pandas as pd

from src.portfolio_watch.infra.market_data.news_source import (
    CafefNewsSource,
    _parse_cafef_html,
)
from src.portfolio_watch.infra.market_data.price_source import VnstockPriceSource


def test_parse_cafef_html_extracts_items():
    html = """
    <ul class="News_Title_Link">
      <li><span>16/09/2026 10:00</span>
          <a href="/fpt-123/fpt-cong-bo-kqkd.chn">FPT công bố KQKD</a></li>
      <li><span>15/09/2026 09:00</span>
          <a href="https://s.cafef.vn/other.chn">Tin khác về thị trường</a></li>
    </ul>
    """
    items = _parse_cafef_html(html, "FPT")
    assert len(items) == 2
    assert items[0].title.startswith("FPT")
    assert items[0].url.startswith("https://")
    assert items[0].published_at.startswith("16/09/2026")


def test_cafef_fetch_news_filters_query(monkeypatch):
    html = """
    <ul class="News_Title_Link">
      <li><span>16/09/2026</span><a href="/a.chn">FPT lãi lớn</a></li>
      <li><span>16/09/2026</span><a href="/b.chn">VNM tăng giá sữa</a></li>
    </ul>
    """
    src = CafefNewsSource()
    monkeypatch.setattr(src, "_http_get", lambda url: html)
    items = src.fetch_news("FPT", query="FPT")
    assert len(items) == 1
    assert "FPT" in items[0].title


def test_cafef_fetch_news_filters_days(monkeypatch):
    html = """
    <ul class="News_Title_Link">
      <li><span>16/09/2026</span><a href="/a.chn">FPT mới</a></li>
      <li><span>01/01/2020</span><a href="/b.chn">FPT cũ</a></li>
    </ul>
    """
    src = CafefNewsSource()
    monkeypatch.setattr(src, "_http_get", lambda url: html)
    items = src.fetch_news("FPT", days=30)
    assert len(items) == 1
    assert items[0].title == "FPT mới"


def test_cafef_fetch_news_http_error_raises(monkeypatch):
    """Timeout/lỗi mạng → raise (NewsAgent bắt → error rõ), không nuốt thành []."""
    import pytest

    src = CafefNewsSource()

    def boom(url):
        raise TimeoutError("timeout")

    monkeypatch.setattr(src, "_http_get", boom)
    with pytest.raises(TimeoutError, match="timeout"):
        src.fetch_news("FPT")


def test_vnstock_price_source_from_dataframe():
    class FakeQuote:
        def __init__(self, symbol, source):
            self.symbol = symbol

        def history(self, start, end, interval="1D"):
            return pd.DataFrame({"close": [100.0, 102.5]})

    src = VnstockPriceSource(quote_factory=FakeQuote)
    quote = src.fetch_latest_close("fpt")
    assert quote.error is None
    assert quote.symbol == "FPT"
    assert quote.latest_close == 102.5
    assert quote.prev_close == 100.0


def test_vnstock_price_source_sorts_by_time():
    class FakeQuote:
        def __init__(self, symbol, source):
            pass

        def history(self, start, end, interval="1D"):
            return pd.DataFrame(
                {
                    "time": ["2026-09-16", "2026-09-15", "2026-09-14"],
                    "close": [30.0, 20.0, 10.0],
                }
            )

    quote = VnstockPriceSource(quote_factory=FakeQuote).fetch_latest_close("FPT")
    assert quote.error is None
    assert quote.latest_close == 30.0
    assert quote.prev_close == 20.0


def test_vnstock_price_source_close_column_case_insensitive():
    class FakeQuote:
        def __init__(self, symbol, source):
            pass

        def history(self, start, end, interval="1D"):
            return pd.DataFrame({"Close": [100.0, 105.0]})

    quote = VnstockPriceSource(quote_factory=FakeQuote).fetch_latest_close("FPT")
    assert quote.error is None
    assert quote.latest_close == 105.0
    assert quote.prev_close == 100.0


def test_vnstock_price_source_empty_df_and_raise():
    class EmptyQuote:
        def __init__(self, symbol, source):
            pass

        def history(self, start, end, interval="1D"):
            return pd.DataFrame({"close": []})

    class BoomQuote:
        def __init__(self, symbol, source):
            raise RuntimeError("network down")

        def history(self, start, end, interval="1D"):
            raise AssertionError("unreachable")

    empty = VnstockPriceSource(quote_factory=EmptyQuote).fetch_latest_close("FPT")
    assert empty.latest_close is None
    assert empty.error

    boom = VnstockPriceSource(quote_factory=BoomQuote).fetch_latest_close("FPT")
    assert boom.latest_close is None
    assert boom.error and "không lấy được dữ liệu giá" in boom.error


def test_vnstock_price_source_empty_symbol():
    src = VnstockPriceSource()
    quote = src.fetch_latest_close("  ")
    assert quote.latest_close is None
    assert quote.error
