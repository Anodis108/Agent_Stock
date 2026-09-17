"""PriceSource thật — vnstock Quote.history (OHLCV theo ngày)."""

from __future__ import annotations

from datetime import datetime, timedelta

from src.portfolio_watch.domain.ports import PriceQuote


class VnstockPriceSource:
    """Lấy giá đóng cửa mới nhất + phiên trước qua vnstock."""

    def __init__(
        self,
        source: str = "VCI",
        lookback_days: int = 14,
        quote_factory=None,
    ):
        self.source = source
        self.lookback_days = lookback_days
        self._quote_factory = quote_factory

    def fetch_latest_close(self, symbol: str) -> PriceQuote:
        sym = (symbol or "").strip().upper()
        if not sym:
            return PriceQuote(symbol="", latest_close=None, error="symbol rỗng")

        try:
            Quote = self._quote_factory
            if Quote is None:
                from vnstock import Quote
            quote = Quote(symbol=sym, source=self.source)
            end = datetime.now().date()
            start = end - timedelta(days=max(self.lookback_days, 5))
            df = quote.history(
                start=start.isoformat(),
                end=end.isoformat(),
                interval="1D",
            )
        except Exception as exc:  # noqa: BLE001
            return PriceQuote(
                symbol=sym,
                latest_close=None,
                error=f"không lấy được dữ liệu giá: {exc}",
            )

        if df is None or getattr(df, "empty", True):
            return PriceQuote(
                symbol=sym,
                latest_close=None,
                error="không lấy được dữ liệu giá",
            )

        try:
            work = df.copy()
            work.columns = [str(c).strip().lower() for c in work.columns]
            if "close" not in work.columns:
                return PriceQuote(
                    symbol=sym,
                    latest_close=None,
                    error="không lấy được dữ liệu giá: thiếu cột close",
                )
            if "time" in work.columns:
                work = work.sort_values("time")
            closes = work["close"].dropna().tolist()
        except Exception as exc:  # noqa: BLE001
            return PriceQuote(
                symbol=sym,
                latest_close=None,
                error=f"không lấy được dữ liệu giá: {exc}",
            )

        if not closes:
            return PriceQuote(
                symbol=sym,
                latest_close=None,
                error="không lấy được dữ liệu giá",
            )

        latest = float(closes[-1])
        prev = float(closes[-2]) if len(closes) >= 2 else None
        return PriceQuote(
            symbol=sym,
            latest_close=latest,
            prev_close=prev,
            error=None,
        )
