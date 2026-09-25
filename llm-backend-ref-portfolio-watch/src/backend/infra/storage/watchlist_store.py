from __future__ import annotations

import sqlite3

from backend.domain.entities import WatchlistItem
from backend.infra.storage.sqlite_db import connect


class SqliteWatchlistStore:
    def __init__(self, db_path: str):
        self._db_path = db_path

    def _conn(self) -> sqlite3.Connection:
        return connect(self._db_path)

    def list_items(self, user_id: str = "default") -> list[WatchlistItem]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT user_id, symbol, threshold_pct FROM watchlist "
                "WHERE user_id = ? ORDER BY symbol",
                (user_id,),
            ).fetchall()
        return [
            WatchlistItem(
                user_id=r["user_id"],
                symbol=r["symbol"],
                threshold_pct=float(r["threshold_pct"]),
            )
            for r in rows
        ]

    def get(self, user_id: str, symbol: str) -> WatchlistItem | None:
        sym = symbol.strip().upper()
        with self._conn() as conn:
            row = conn.execute(
                "SELECT user_id, symbol, threshold_pct FROM watchlist "
                "WHERE user_id = ? AND symbol = ?",
                (user_id, sym),
            ).fetchone()
        if row is None:
            return None
        return WatchlistItem(
            user_id=row["user_id"],
            symbol=row["symbol"],
            threshold_pct=float(row["threshold_pct"]),
        )

    def upsert(self, item: WatchlistItem) -> WatchlistItem:
        sym = item.symbol.strip().upper()
        saved = WatchlistItem(
            user_id=item.user_id,
            symbol=sym,
            threshold_pct=item.threshold_pct,
        )
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO watchlist (user_id, symbol, threshold_pct) VALUES (?, ?, ?) "
                "ON CONFLICT(user_id, symbol) DO UPDATE SET threshold_pct = excluded.threshold_pct",
                (saved.user_id, saved.symbol, saved.threshold_pct),
            )
            conn.commit()
        return saved

    def delete(self, user_id: str, symbol: str) -> bool:
        sym = symbol.strip().upper()
        with self._conn() as conn:
            cur = conn.execute(
                "DELETE FROM watchlist WHERE user_id = ? AND symbol = ?",
                (user_id, sym),
            )
            conn.commit()
            return cur.rowcount > 0
