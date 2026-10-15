"""Repository for Portfolio Holdings and User Settings in Web Backend."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class PortfolioHoldingRecord:
    id: str
    user_id: str
    symbol: str
    quantity: float
    avg_buy_price: float
    purchase_date: str | None
    created_at: str
    updated_at: str


@dataclass
class UserSettingsRecord:
    user_id: str
    alert_threshold_pct: float
    updated_at: str


class PortfolioHoldingRepository:
    def __init__(self, conn: Any) -> None:
        self.conn = conn

    def create(
        self,
        symbol: str,
        quantity: float,
        avg_buy_price: float,
        user_id: str = "default",
        purchase_date: str | None = None,
        holding_id: str | None = None,
    ) -> PortfolioHoldingRecord:
        hid = holding_id or str(uuid4())
        sym = symbol.strip().upper()
        now = _now_iso()
        p_date = purchase_date or now[:10]
        self.conn.execute(
            """
            INSERT INTO portfolio_holdings (id, user_id, symbol, quantity, avg_buy_price, purchase_date, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (hid, user_id, sym, float(quantity), float(avg_buy_price), p_date, now, now),
        )
        self.conn.commit()
        return PortfolioHoldingRecord(
            id=hid,
            user_id=user_id,
            symbol=sym,
            quantity=float(quantity),
            avg_buy_price=float(avg_buy_price),
            purchase_date=p_date,
            created_at=now,
            updated_at=now,
        )

    def get(self, holding_id: str) -> PortfolioHoldingRecord | None:
        cursor = self.conn.execute(
            """
            SELECT id, user_id, symbol, quantity, avg_buy_price, purchase_date, created_at, updated_at
            FROM portfolio_holdings WHERE id = ?
            """,
            (holding_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return PortfolioHoldingRecord(
            id=row["id"],
            user_id=row["user_id"],
            symbol=row["symbol"],
            quantity=float(row["quantity"]),
            avg_buy_price=float(row["avg_buy_price"]),
            purchase_date=row["purchase_date"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def list_by_user(self, user_id: str = "default") -> list[PortfolioHoldingRecord]:
        cursor = self.conn.execute(
            """
            SELECT id, user_id, symbol, quantity, avg_buy_price, purchase_date, created_at, updated_at
            FROM portfolio_holdings WHERE user_id = ? ORDER BY symbol ASC
            """,
            (user_id,),
        )
        return [
            PortfolioHoldingRecord(
                id=row["id"],
                user_id=row["user_id"],
                symbol=row["symbol"],
                quantity=float(row["quantity"]),
                avg_buy_price=float(row["avg_buy_price"]),
                purchase_date=row["purchase_date"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            for row in cursor.fetchall()
        ]

    def update(
        self,
        holding_id: str,
        quantity: float | None = None,
        avg_buy_price: float | None = None,
        purchase_date: str | None = None,
    ) -> bool:
        fields = []
        params = []
        if quantity is not None:
            fields.append("quantity = ?")
            params.append(float(quantity))
        if avg_buy_price is not None:
            fields.append("avg_buy_price = ?")
            params.append(float(avg_buy_price))
        if purchase_date is not None:
            fields.append("purchase_date = ?")
            params.append(purchase_date)
        if not fields:
            return False
        fields.append("updated_at = ?")
        params.append(_now_iso())
        params.append(holding_id)
        sql = f"UPDATE portfolio_holdings SET {', '.join(fields)} WHERE id = ?"
        cursor = self.conn.execute(sql, tuple(params))
        self.conn.commit()
        return cursor.rowcount > 0

    def delete(self, holding_id: str, user_id: str | None = None) -> bool:
        if user_id:
            cursor = self.conn.execute(
                "DELETE FROM portfolio_holdings WHERE id = ? AND user_id = ?",
                (holding_id, user_id),
            )
        else:
            cursor = self.conn.execute(
                "DELETE FROM portfolio_holdings WHERE id = ?",
                (holding_id,),
            )
        self.conn.commit()
        return cursor.rowcount > 0


class UserSettingsRepository:
    def __init__(self, conn: Any) -> None:
        self.conn = conn

    def get(self, user_id: str = "default") -> UserSettingsRecord:
        cursor = self.conn.execute(
            "SELECT user_id, alert_threshold_pct, updated_at FROM user_settings WHERE user_id = ?",
            (user_id,),
        )
        row = cursor.fetchone()
        if not row:
            return UserSettingsRecord(user_id=user_id, alert_threshold_pct=3.0, updated_at=_now_iso())
        return UserSettingsRecord(
            user_id=row["user_id"],
            alert_threshold_pct=float(row["alert_threshold_pct"]),
            updated_at=row["updated_at"],
        )

    def set_threshold(self, user_id: str, alert_threshold_pct: float) -> UserSettingsRecord:
        now = _now_iso()
        self.conn.execute(
            """
            INSERT INTO user_settings (user_id, alert_threshold_pct, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                alert_threshold_pct = excluded.alert_threshold_pct,
                updated_at = excluded.updated_at
            """,
            (user_id, float(alert_threshold_pct), now),
        )
        self.conn.commit()
        return UserSettingsRecord(user_id=user_id, alert_threshold_pct=float(alert_threshold_pct), updated_at=now)


# Short aliases
PortfolioRepo = PortfolioHoldingRepository
UserSettingsRepo = UserSettingsRepository
