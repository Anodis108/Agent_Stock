"""Market Service for 10-day market history synchronization and matrix computation.

Provides:
- Synchronization of 10-day OHLCV price history for 10 key Vietnamese tickers
  (FPT, VNM, HPG, VHM, VIC, TCB, MBB, SSI, MWG, VCB).
- Caching into the SQLite `market_history_10d` table.
- Matrix data preparation with sparkline series, daily percentage changes, and volumes.
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Any

from backend.database.connection import get_connection
from backend.database.repositories import MarketHistoryRecord, MarketHistoryRepository
from backend.domain.ports import PriceBar
from backend.infra.market_data.price_source import VnstockPriceSource

logger = logging.getLogger(__name__)

# 10 default blue-chip tickers for the Market Watch Matrix
DEFAULT_MARKET_SYMBOLS: list[str] = [
    "FPT",
    "VNM",
    "HPG",
    "VHM",
    "VIC",
    "TCB",
    "MBB",
    "SSI",
    "MWG",
    "VCB",
]

# Baseline prices in thousands of VND used for realistic synthetic fallbacks if API is offline
DEFAULT_BASE_PRICES: dict[str, float] = {
    "FPT": 66.0,  # Đồng bộ thị giá thực tế (~65.x - 66.x), loại bỏ mốc 135.0 cũ
    "VNM": 61.0,
    "HPG": 21.0,
    "VHM": 66.0,
    "VIC": 45.0,
    "TCB": 33.0,
    "MBB": 20.0,
    "SSI": 21.0,
    "MWG": 73.0,
    "VCB": 58.0,
}


class MarketService:
    """Service handling synchronization, caching, and matrix computation for market history."""

    def __init__(
        self,
        conn: sqlite3.Connection | None = None,
        price_source: VnstockPriceSource | None = None,
        history_repo: MarketHistoryRepository | None = None,
    ):
        if history_repo is not None:
            self.repo = history_repo
            self.conn = history_repo.conn
        else:
            self.conn = conn or get_connection()
            self.repo = MarketHistoryRepository(self.conn)

        self.price_source = price_source or VnstockPriceSource()

    def _synthesize_fallback_bars(self, symbol: str, count: int = 10) -> list[PriceBar]:
        """Generate realistic synthetic bars when live vnstock API is unavailable.

        Ensures zero-crash robustness in offline, test, or rate-limited environments.
        Anchors the latest bar directly to the current market quote (Single Source of Truth).
        """
        sym = symbol.strip().upper()
        # Single Source of Truth: Ưu tiên lấy giá từ cache của price_source nếu có
        cached_quote = None
        try:
            cached_quote = self.price_source.fetch_latest_close(sym)
        except Exception:
            pass

        if cached_quote and cached_quote.latest_close and not cached_quote.error:
            base_price = cached_quote.latest_close
            known_prev = cached_quote.prev_close
        else:
            base_price = DEFAULT_BASE_PRICES.get(sym, 50.0)
            known_prev = round(base_price * 0.99, 2)

        today = datetime.now().date()
        # Collect recent weekdays
        dates: list[str] = []
        curr = today
        while len(dates) < count:
            if curr.weekday() < 5:  # Monday to Friday
                dates.append(curr.isoformat())
            curr -= timedelta(days=1)
        dates.reverse()

        # Compute closes anchored backwards so the latest bar (today) equals base_price exactly
        closes: list[float] = [0.0] * len(dates)
        closes[-1] = base_price
        if len(dates) >= 2 and known_prev:
            closes[-2] = known_prev

        start_back = len(dates) - 3 if (len(dates) >= 2 and known_prev) else len(dates) - 2
        for i in range(start_back, -1, -1):
            drift_pct = (((i * 7 + hash(sym)) % 11) - 5) * 0.005
            prev_val = closes[i + 1] / (1.0 + drift_pct)
            closes[i] = round(max(prev_val, 1.0), 2)

        bars: list[PriceBar] = []
        for i, d_str in enumerate(dates):
            p = closes[i]
            open_p = round(p * 0.995, 2)
            high_p = round(max(open_p, p) * 1.01, 2)
            low_p = round(min(open_p, p) * 0.99, 2)
            vol = 1_500_000 + ((i * 31 + hash(sym)) % 1_000_000)

            bars.append(
                PriceBar(
                    date=d_str,
                    close=p,
                    open_price=open_p,
                    high=high_p,
                    low=low_p,
                    volume=float(vol),
                )
            )
        return bars

    def sync_symbol_history(
        self,
        symbol: str,
        days: int = 15,
        fallback_on_empty: bool = True,
    ) -> list[MarketHistoryRecord]:
        """Fetch 10+ daily bars via PriceSource, calculate change_pct, and cache into SQLite."""
        sym = symbol.strip().upper()
        if not sym:
            return []

        bars: list[PriceBar] = []
        try:
            bars = self.price_source.fetch_history(sym, days=days)
        except Exception as exc:
            logger.warning("Failed fetching history for %s via PriceSource: %s", sym, exc)

        if not bars and fallback_on_empty:
            logger.info("Synthesizing fallback bars for %s (offline/test mode)", sym)
            bars = self._synthesize_fallback_bars(sym, count=min(days, 10))

        if not bars:
            return []

        # Sort chronologically ascending
        bars.sort(key=lambda b: b.date)

        records: list[MarketHistoryRecord] = []
        for i, bar in enumerate(bars):
            if i == 0:
                # First bar: calculate against open if available, else 0.0
                if bar.open_price and bar.open_price > 0:
                    chg_pct = round(((bar.close - bar.open_price) / bar.open_price) * 100.0, 2)
                else:
                    chg_pct = 0.0
            else:
                prev_close = bars[i - 1].close
                if prev_close and prev_close > 0:
                    chg_pct = round(((bar.close - prev_close) / prev_close) * 100.0, 2)
                else:
                    chg_pct = 0.0

            records.append(
                MarketHistoryRecord(
                    symbol=sym,
                    trade_date=bar.date,
                    open=bar.open_price,
                    high=bar.high,
                    low=bar.low,
                    close=bar.close,
                    volume=int(bar.volume) if bar.volume is not None else None,
                    change_pct=chg_pct,
                )
            )

        self.repo.bulk_upsert(records)
        return records

    def sync_all_default_symbols(self, days: int = 15) -> dict[str, list[MarketHistoryRecord]]:
        """Sync history for all 10 default tickers and persist into market_history_10d."""
        results: dict[str, list[MarketHistoryRecord]] = {}
        for sym in DEFAULT_MARKET_SYMBOLS:
            records = self.sync_symbol_history(sym, days=days)
            results[sym] = records
        return results

    def get_symbol_history(
        self,
        symbol: str,
        limit: int = 10,
        auto_sync: bool = True,
    ) -> list[MarketHistoryRecord]:
        """Retrieve the latest `limit` trading bars from SQLite, auto-syncing if empty."""
        sym = symbol.strip().upper()
        records = self.repo.get_history(sym, limit=limit, ascending=True)

        if len(records) < limit and auto_sync:
            self.sync_symbol_history(sym, days=limit + 5)
            records = self.repo.get_history(sym, limit=limit, ascending=True)

        return records

    def get_matrix_10d(
        self,
        symbols: list[str] | None = None,
        days: int = 10,
        auto_sync: bool = True,
    ) -> list[dict[str, Any]]:
        """Generate structured 10-day market matrix data for the frontend table and API.

        Each symbol entry contains:
        - symbol: str
        - current_price: float
        - change_pct: float (latest day % change)
        - total_volume: int (total volume over 10 days)
        - sparkline: list[float] (close prices for SVG sparkline)
        - sessions: list[dict] (up to 10 trading sessions ordered chronologically)
        """
        target_symbols = symbols or DEFAULT_MARKET_SYMBOLS
        matrix: list[dict[str, Any]] = []

        for sym in target_symbols:
            bars = self.get_symbol_history(sym, limit=days, auto_sync=auto_sync)
            if not bars:
                continue

            latest_bar = bars[-1]
            sparkline_prices = [b.close for b in bars]
            tot_vol = sum(b.volume or 0 for b in bars)

            session_list = [
                {
                    "date": b.trade_date,
                    "open": b.open,
                    "high": b.high,
                    "low": b.low,
                    "close": b.close,
                    "volume": b.volume,
                    "change_pct": b.change_pct,
                }
                for b in bars
            ]

            matrix.append(
                {
                    "symbol": sym,
                    "current_price": latest_bar.close,
                    "change_pct": latest_bar.change_pct,
                    "total_volume": tot_vol,
                    "sparkline": sparkline_prices,
                    "sessions": session_list,
                }
            )

        return matrix


def get_market_service(
    conn: sqlite3.Connection | None = None,
    price_source: VnstockPriceSource | None = None,
) -> MarketService:
    """Factory helper to obtain a MarketService instance sharing the configured PriceSource."""
    if price_source is None:
        try:
            from backend.api.deps import get_app_deps
            price_source = get_app_deps().price_source
        except Exception:
            price_source = None
    return MarketService(conn=conn, price_source=price_source)


def sync_market_data(conn: sqlite3.Connection | None = None) -> dict[str, list[MarketHistoryRecord]]:
    """Synchronize all default symbols and cache in SQLite."""
    service = get_market_service(conn=conn)
    return service.sync_all_default_symbols()
