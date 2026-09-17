from __future__ import annotations

import sqlite3
from datetime import date, timedelta

from src.portfolio_watch.domain.ports import PriceBar
from src.portfolio_watch.infra.storage.sqlite_db import connect


class SqlitePriceHistoryStore:
    def __init__(self, db_path: str):
        self._db_path = db_path

    def _conn(self) -> sqlite3.Connection:
        return connect(self._db_path)

    def read_history(self, symbol: str, days: int = 30) -> list[PriceBar]:
        sym = symbol.strip().upper()
        since = (date.today() - timedelta(days=max(days, 1))).isoformat()
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT date, close, open_price, high, low, volume "
                "FROM price_history WHERE symbol = ? AND date >= ? "
                "ORDER BY date ASC",
                (sym, since),
            ).fetchall()
        return [
            PriceBar(
                date=r["date"],
                close=float(r["close"]),
                open_price=None if r["open_price"] is None else float(r["open_price"]),
                high=None if r["high"] is None else float(r["high"]),
                low=None if r["low"] is None else float(r["low"]),
                volume=None if r["volume"] is None else float(r["volume"]),
            )
            for r in rows
        ]

    def upsert_bars(self, symbol: str, bars: list[PriceBar]) -> None:
        """Ghi lịch sử giá (dùng khi ingest / test) — không nằm trên Protocol."""
        sym = symbol.strip().upper()
        with self._conn() as conn:
            conn.executemany(
                "INSERT INTO price_history "
                "(symbol, date, close, open_price, high, low, volume) "
                "VALUES (?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(symbol, date) DO UPDATE SET "
                "close = excluded.close, open_price = excluded.open_price, "
                "high = excluded.high, low = excluded.low, volume = excluded.volume",
                [
                    (
                        sym,
                        b.date,
                        b.close,
                        b.open_price,
                        b.high,
                        b.low,
                        b.volume,
                    )
                    for b in bars
                ],
            )
            conn.commit()
