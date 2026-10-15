"""Repository for Watchlist management in Web Backend."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class WatchlistRecord:
    symbol: str
    threshold_pct: float
    updated_at: str
    user_id: str = "default"


class WatchlistRepository:
    def __init__(self, conn: Any) -> None:
        self.conn = conn

    def upsert(
        self,
        symbol: Any = None,
        threshold_pct: float = 3.0,
        user_id: str = "default",
        item: Any = None,
    ) -> WatchlistRecord:
        target = item if item is not None else symbol
        if hasattr(target, "symbol"):
            sym = str(target.symbol).strip().upper()
            threshold_pct = float(getattr(target, "threshold_pct", threshold_pct))
            user_id = str(getattr(target, "user_id", user_id))
        else:
            sym = str(target).strip().upper()
            threshold_pct = float(threshold_pct)
            user_id = str(user_id)
        now = _now_iso()
        try:
            self.conn.execute(
                """
                INSERT INTO watchlist (symbol, threshold_pct, updated_at, user_id)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id, symbol) DO UPDATE SET
                    threshold_pct = excluded.threshold_pct,
                    updated_at = excluded.updated_at
                """,
                (sym, float(threshold_pct), now, user_id),
            )
        except (sqlite3.OperationalError, Exception):
            self.conn.execute(
                """
                INSERT INTO watchlist (symbol, threshold_pct, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(symbol) DO UPDATE SET
                    threshold_pct = excluded.threshold_pct,
                    updated_at = excluded.updated_at
                """,
                (sym, float(threshold_pct), now),
            )
        self.conn.commit()
        return WatchlistRecord(symbol=sym, threshold_pct=float(threshold_pct), updated_at=now, user_id=user_id)

    def get(self, symbol: str, user_id: str = "default") -> WatchlistRecord | None:
        try:
            cursor = self.conn.execute(
                "SELECT symbol, threshold_pct, updated_at, user_id FROM watchlist WHERE (symbol = ? AND user_id = ?) OR (symbol = ? AND user_id = ?)",
                (symbol.strip().upper(), user_id, user_id.strip().upper(), symbol),
            )
            row = cursor.fetchone()
        except (sqlite3.OperationalError, Exception):
            sym = symbol.strip().upper() if len(symbol) <= 10 else user_id.strip().upper()
            cursor = self.conn.execute(
                "SELECT symbol, threshold_pct, updated_at FROM watchlist WHERE symbol = ?",
                (sym,),
            )
            row = cursor.fetchone()
        if not row:
            return None
        return WatchlistRecord(
            symbol=row["symbol"],
            threshold_pct=float(row["threshold_pct"]),
            updated_at=row["updated_at"],
            user_id=row["user_id"] if "user_id" in row.keys() else user_id,
        )

    def list_all(self, user_id: str | None = "default") -> list[WatchlistRecord]:
        try:
            if user_id:
                cursor = self.conn.execute(
                    "SELECT symbol, threshold_pct, updated_at, user_id FROM watchlist WHERE user_id = ? ORDER BY symbol ASC",
                    (user_id,),
                )
            else:
                cursor = self.conn.execute(
                    "SELECT symbol, threshold_pct, updated_at, user_id FROM watchlist ORDER BY symbol ASC"
                )
        except (sqlite3.OperationalError, Exception):
            cursor = self.conn.execute(
                "SELECT symbol, threshold_pct, updated_at FROM watchlist ORDER BY symbol ASC"
            )
        return [
            WatchlistRecord(
                symbol=row["symbol"],
                threshold_pct=float(row["threshold_pct"]),
                updated_at=row["updated_at"],
                user_id=row["user_id"] if "user_id" in row.keys() else (user_id or "default"),
            )
            for row in cursor.fetchall()
        ]

    def list_items(self, user_id: str = "default") -> list[WatchlistRecord]:
        return self.list_all(user_id)

    def delete(self, symbol: str, user_id: str = "default") -> bool:
        try:
            cursor = self.conn.execute(
                "DELETE FROM watchlist WHERE (symbol = ? AND user_id = ?) OR (symbol = ? AND user_id = ?)",
                (symbol.strip().upper(), user_id, user_id.strip().upper(), symbol),
            )
        except (sqlite3.OperationalError, Exception):
            sym = symbol.strip().upper() if len(symbol) <= 10 else user_id.strip().upper()
            cursor = self.conn.execute("DELETE FROM watchlist WHERE symbol = ?", (sym,))
        self.conn.commit()
        return cursor.rowcount > 0


# Short alias
WatchlistRepo = WatchlistRepository
