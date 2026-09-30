"""Repository classes implementing clean CRUD helpers for SQLite database tables.

Entities:
- SessionRepository -> sessions table
- MessageRepository -> messages table
- MarketHistoryRepository -> market_history_10d table
- HITLEvaluationRepository -> hitl_evaluations table
- WatchlistRepository -> watchlist table
"""

from __future__ import annotations

import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def _now_iso() -> str:
    """Return current UTC time in ISO format."""
    return datetime.now(timezone.utc).isoformat()


@dataclass
class SessionRecord:
    id: str
    title: str
    created_at: str
    updated_at: str


@dataclass
class MessageRecord:
    id: str
    session_id: str
    role: str  # "user" | "assistant" | "system"
    content: str
    chart_path: str | None
    trace_data: str | None
    created_at: str


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


@dataclass
class HITLEvaluationRecord:
    id: str
    message_id: str
    session_id: str
    rating: int | None
    feedback: str | None
    is_positive: bool
    created_at: str
    reason: str | None = None
    question: str | None = None
    answer: str | None = None


@dataclass
class WatchlistRecord:
    symbol: str
    threshold_pct: float
    updated_at: str
    user_id: str = "default"


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


class SessionRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def create(self, title: str = "Cuộc trò chuyện mới", session_id: str | None = None) -> SessionRecord:
        sid = session_id or str(uuid4())
        now = _now_iso()
        self.conn.execute(
            "INSERT INTO sessions (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (sid, title, now, now),
        )
        self.conn.commit()
        return SessionRecord(id=sid, title=title, created_at=now, updated_at=now)

    def get(self, session_id: str) -> SessionRecord | None:
        cursor = self.conn.execute(
            "SELECT id, title, created_at, updated_at FROM sessions WHERE id = ?",
            (session_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return SessionRecord(
            id=row["id"],
            title=row["title"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def list_all(self, limit: int = 50) -> list[SessionRecord]:
        cursor = self.conn.execute(
            "SELECT id, title, created_at, updated_at FROM sessions ORDER BY updated_at DESC LIMIT ?",
            (limit,),
        )
        return [
            SessionRecord(
                id=row["id"],
                title=row["title"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            for row in cursor.fetchall()
        ]

    def update_title(self, session_id: str, title: str) -> bool:
        now = _now_iso()
        cursor = self.conn.execute(
            "UPDATE sessions SET title = ?, updated_at = ? WHERE id = ?",
            (title, now, session_id),
        )
        self.conn.commit()
        return cursor.rowcount > 0

    def touch(self, session_id: str) -> bool:
        now = _now_iso()
        cursor = self.conn.execute(
            "UPDATE sessions SET updated_at = ? WHERE id = ?",
            (now, session_id),
        )
        self.conn.commit()
        return cursor.rowcount > 0

    def delete(self, session_id: str) -> bool:
        cursor = self.conn.execute(
            "DELETE FROM sessions WHERE id = ?",
            (session_id,),
        )
        self.conn.commit()
        return cursor.rowcount > 0


class MessageRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def create(
        self,
        session_id: str,
        role: str,
        content: str,
        chart_path: str | None = None,
        trace_data: str | None = None,
        message_id: str | None = None,
    ) -> MessageRecord:
        mid = message_id or str(uuid4())
        now = _now_iso()
        self.conn.execute(
            """
            INSERT INTO messages (id, session_id, role, content, chart_path, trace_data, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (mid, session_id, role, content, chart_path, trace_data, now),
        )
        # Update session's updated_at
        self.conn.execute(
            "UPDATE sessions SET updated_at = ? WHERE id = ?",
            (now, session_id),
        )
        self.conn.commit()
        return MessageRecord(
            id=mid,
            session_id=session_id,
            role=role,
            content=content,
            chart_path=chart_path,
            trace_data=trace_data,
            created_at=now,
        )

    def list_by_session(self, session_id: str) -> list[MessageRecord]:
        cursor = self.conn.execute(
            """
            SELECT id, session_id, role, content, chart_path, trace_data, created_at
            FROM messages
            WHERE session_id = ?
            ORDER BY created_at ASC
            """,
            (session_id,),
        )
        return [
            MessageRecord(
                id=row["id"],
                session_id=row["session_id"],
                role=row["role"],
                content=row["content"],
                chart_path=row["chart_path"],
                trace_data=row["trace_data"],
                created_at=row["created_at"],
            )
            for row in cursor.fetchall()
        ]

    def get(self, message_id: str) -> MessageRecord | None:
        cursor = self.conn.execute(
            """
            SELECT id, session_id, role, content, chart_path, trace_data, created_at
            FROM messages
            WHERE id = ?
            """,
            (message_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return MessageRecord(
            id=row["id"],
            session_id=row["session_id"],
            role=row["role"],
            content=row["content"],
            chart_path=row["chart_path"],
            trace_data=row["trace_data"],
            created_at=row["created_at"],
        )


class MarketHistoryRepository:
    def __init__(self, conn: sqlite3.Connection):
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
        # Always fetch the latest `limit` trading days, ordered as requested
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


class HITLEvaluationRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def create(
        self,
        message_id: str,
        session_id: str,
        is_positive: bool,
        rating: int | None = None,
        feedback: str | None = None,
        reason: str | None = None,
        question: str | None = None,
        answer: str | None = None,
        eval_id: str | None = None,
    ) -> HITLEvaluationRecord:
        eid = eval_id or str(uuid4())
        now = _now_iso()
        pos_int = 1 if is_positive else 0
        self.conn.execute(
            """
            INSERT INTO hitl_evaluations (id, message_id, session_id, rating, feedback, is_positive, reason, question, answer, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (eid, message_id, session_id, rating, feedback, pos_int, reason, question, answer, now),
        )
        self.conn.commit()
        return HITLEvaluationRecord(
            id=eid,
            message_id=message_id,
            session_id=session_id,
            rating=rating,
            feedback=feedback,
            is_positive=is_positive,
            created_at=now,
            reason=reason,
            question=question,
            answer=answer,
        )

    def get(self, eval_id: str) -> HITLEvaluationRecord | None:
        cursor = self.conn.execute(
            """
            SELECT id, message_id, session_id, rating, feedback, is_positive, reason, question, answer, created_at
            FROM hitl_evaluations
            WHERE id = ?
            """,
            (eval_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return HITLEvaluationRecord(
            id=row["id"],
            message_id=row["message_id"],
            session_id=row["session_id"],
            rating=row["rating"],
            feedback=row["feedback"],
            is_positive=bool(row["is_positive"]),
            reason=row["reason"] if "reason" in row.keys() else None,
            question=row["question"] if "question" in row.keys() else None,
            answer=row["answer"] if "answer" in row.keys() else None,
            created_at=row["created_at"],
        )

    def list_by_session(self, session_id: str) -> list[HITLEvaluationRecord]:
        cursor = self.conn.execute(
            """
            SELECT id, message_id, session_id, rating, feedback, is_positive, reason, question, answer, created_at
            FROM hitl_evaluations
            WHERE session_id = ?
            ORDER BY created_at DESC
            """,
            (session_id,),
        )
        return [
            HITLEvaluationRecord(
                id=row["id"],
                message_id=row["message_id"],
                session_id=row["session_id"],
                rating=row["rating"],
                feedback=row["feedback"],
                is_positive=bool(row["is_positive"]),
                reason=row["reason"] if "reason" in row.keys() else None,
                question=row["question"] if "question" in row.keys() else None,
                answer=row["answer"] if "answer" in row.keys() else None,
                created_at=row["created_at"],
            )
            for row in cursor.fetchall()
        ]

    def list_all(self, limit: int = 100) -> list[HITLEvaluationRecord]:
        cursor = self.conn.execute(
            """
            SELECT id, message_id, session_id, rating, feedback, is_positive, reason, question, answer, created_at
            FROM hitl_evaluations
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [
            HITLEvaluationRecord(
                id=row["id"],
                message_id=row["message_id"],
                session_id=row["session_id"],
                rating=row["rating"],
                feedback=row["feedback"],
                is_positive=bool(row["is_positive"]),
                reason=row["reason"] if "reason" in row.keys() else None,
                question=row["question"] if "question" in row.keys() else None,
                answer=row["answer"] if "answer" in row.keys() else None,
                created_at=row["created_at"],
            )
            for row in cursor.fetchall()
        ]


class WatchlistRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def upsert(self, symbol: str, threshold_pct: float = 3.0, user_id: str = "default") -> WatchlistRecord:
        sym = symbol.strip().upper()
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
        except sqlite3.OperationalError:
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
        sym = symbol.strip().upper()
        try:
            cursor = self.conn.execute(
                "SELECT symbol, threshold_pct, updated_at, user_id FROM watchlist WHERE symbol = ? AND user_id = ?",
                (sym, user_id),
            )
            row = cursor.fetchone()
        except sqlite3.OperationalError:
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
        except sqlite3.OperationalError:
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

    def delete(self, symbol: str, user_id: str = "default") -> bool:
        sym = symbol.strip().upper()
        try:
            cursor = self.conn.execute(
                "DELETE FROM watchlist WHERE symbol = ? AND user_id = ?",
                (sym, user_id),
            )
        except sqlite3.OperationalError:
            cursor = self.conn.execute("DELETE FROM watchlist WHERE symbol = ?", (sym,))
        self.conn.commit()
        return cursor.rowcount > 0


class PortfolioHoldingRepository:
    def __init__(self, conn: sqlite3.Connection):
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
    def __init__(self, conn: sqlite3.Connection):
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

