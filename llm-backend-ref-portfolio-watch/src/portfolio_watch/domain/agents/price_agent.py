"""PriceAgent — hàm thuần, không LLM: % thay đổi giá so với phiên trước."""

from __future__ import annotations

from dataclasses import dataclass

from src.portfolio_watch.domain.ports import PriceQuote, PriceSource


@dataclass(slots=True)
class PriceAgentResult:
    symbol: str
    latest_close: float | None
    prev_close: float | None
    change_pct: float | None
    error: str | None = None


def run_price_agent(symbol: str, price_source: PriceSource) -> PriceAgentResult:
    try:
        quote = price_source.fetch_latest_close(symbol)
    except Exception as exc:  # noqa: BLE001 — port lỗi không được làm crash agent
        return PriceAgentResult(
            symbol=symbol,
            latest_close=None,
            prev_close=None,
            change_pct=None,
            error=f"không lấy được dữ liệu giá: {exc}",
        )
    if quote is None:
        return PriceAgentResult(
            symbol=symbol,
            latest_close=None,
            prev_close=None,
            change_pct=None,
            error="không lấy được dữ liệu giá",
        )
    return _from_quote(symbol, quote)


def _from_quote(symbol: str, quote: PriceQuote) -> PriceAgentResult:
    if quote.error:
        err = quote.error.strip()
        # test-plan / Phase 5: lỗi rõ, không để message mập mờ kiểu "timeout"
        if err and "không lấy được" not in err.lower():
            err = f"không lấy được dữ liệu giá: {err}"
        return PriceAgentResult(
            symbol=symbol,
            latest_close=quote.latest_close,
            prev_close=quote.prev_close,
            change_pct=None,
            error=err or "không lấy được dữ liệu giá",
        )
    if quote.latest_close is None:
        return PriceAgentResult(
            symbol=symbol,
            latest_close=None,
            prev_close=quote.prev_close,
            change_pct=None,
            error="không lấy được dữ liệu giá",
        )
    if quote.prev_close is None:
        return PriceAgentResult(
            symbol=symbol,
            latest_close=quote.latest_close,
            prev_close=None,
            change_pct=None,
            error="không có giá phiên trước để tính % thay đổi",
        )
    if quote.prev_close == 0:
        return PriceAgentResult(
            symbol=symbol,
            latest_close=quote.latest_close,
            prev_close=quote.prev_close,
            change_pct=None,
            error="giá phiên trước = 0, không tính được % thay đổi",
        )

    change_pct = (quote.latest_close - quote.prev_close) / quote.prev_close * 100.0
    return PriceAgentResult(
        symbol=symbol,
        latest_close=quote.latest_close,
        prev_close=quote.prev_close,
        change_pct=change_pct,
        error=None,
    )
