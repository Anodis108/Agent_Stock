"""Repository for Market History 10D in Web Backend."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class MarketHistoryRecord:
    symbol: str
    trade_date: str
    open: float | None
    high: float | None
    low: float | None
    close: float
    volume: int | None
    change_pct: float | None


class MarketHistoryRepository:
    def __init__(self, conn: Any) -> None:
        self.conn = conn

    def upsert_bar(
        self,
        symbol: str,
        trade_date: str,
        close: float,
        open_: float | None = None,
        high: float | None = None,
        low: float | None = None,
        volume: int | None = None,
        change_pct: float | None = None,
    ) -> MarketHistoryRecord:
        sym = symbol.strip().upper()
        self.conn.execute(
            """
            INSERT INTO market_history_10d (symbol, trade_date, open, high, low, close, volume, change_pct)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(symbol, trade_date) DO UPDATE SET
                open = excluded.open,
                high = excluded.high,
                low = excluded.low,
                close = excluded.close,
                volume = excluded.volume,
                change_pct = excluded.change_pct
            """,
            (sym, trade_date, open_, high, low, close, volume, change_pct),
        )
        self.conn.commit()
        return MarketHistoryRecord(
            symbol=sym,
            trade_date=trade_date,
            open=open_,
            high=high,
            low=low,
            close=close,
            volume=volume,
            change_pct=change_pct,
        )

    def bulk_upsert(self, bars: list[MarketHistoryRecord]) -> None:
        if not bars:
            return
        data = [
            (
                b.symbol.strip().upper(),
                b.trade_date,
                b.open,
                b.high,
                b.low,
                b.close,
                b.volume,
                b.change_pct,
            )
            for b in bars
        ]
        self.conn.executemany(
            """
            INSERT INTO market_history_10d (symbol, trade_date, open, high, low, close, volume, change_pct)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(symbol, trade_date) DO UPDATE SET
                open = excluded.open,
                high = excluded.high,
                low = excluded.low,
                close = excluded.close,
                volume = excluded.volume,
                change_pct = excluded.change_pct
            """,
            data,
        )
        self.conn.commit()

    def get_history(self, symbol: str, limit: int = 10, ascending: bool = True) -> list[MarketHistoryRecord]:
        sym = symbol.strip().upper()
        order = "ASC" if ascending else "DESC"
        cursor = self.conn.execute(
            f"""
            SELECT symbol, trade_date, open, high, low, close, volume, change_pct
            FROM (
                SELECT symbol, trade_date, open, high, low, close, volume, change_pct
                FROM market_history_10d
                WHERE symbol = ?
                ORDER BY trade_date DESC
                LIMIT ?
            )
            ORDER BY trade_date {order}
            """,
            (sym, limit),
        )
        return [
            MarketHistoryRecord(
                symbol=row["symbol"],
                trade_date=row["trade_date"],
                open=row["open"],
                high=row["high"],
                low=row["low"],
                close=row["close"],
                volume=row["volume"],
                change_pct=row["change_pct"],
            )
            for row in cursor.fetchall()
        ]

    def get_tracked_symbols(self) -> list[str]:
        cursor = self.conn.execute("SELECT DISTINCT symbol FROM market_history_10d ORDER BY symbol ASC")
        return [row["symbol"] for row in cursor.fetchall()]


# Short alias
MarketHistoryRepo = MarketHistoryRepository
