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


def has_change_pct_evidence(price: PriceAgentResult | None) -> bool:
    """Đủ evidence giá để so sánh % (Phase 3c)."""
    return (
        price is not None
        and not price.error
        and price.change_pct is not None
    )


def prices_have_change_pct_evidence(
    prices: list[PriceAgentResult],
    symbols: list[str] | None = None,
) -> bool:
    """Mọi mã (hoặc tập symbols) đều có change_pct trước khi so sánh %."""
    if not prices:
        return False
    by_sym = {p.symbol.upper(): p for p in prices if p.symbol}
    targets = [s.upper() for s in symbols] if symbols else list(by_sym)
    if not targets:
        return False
    return all(has_change_pct_evidence(by_sym.get(s)) for s in targets)

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
