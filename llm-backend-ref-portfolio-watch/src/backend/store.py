"""SQLite Store — Quản lý Watchlist, Approvals (HITL) và Runs (One-shot trace).

Tuân thủ kiến trúc Clean Code:
- Lưu trữ bền vững Watchlist và Approvals qua SQLite (mặc định tại resources/data/backend_store.db).
- Quản lý bộ nhớ ngắn hạn của các lượt chạy (RunRecord) trong bộ nhớ.
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class WatchlistItem:
    """Mục cổ phiếu trong danh mục theo dõi của người dùng."""

    symbol: str
    threshold_pct: float
    user_id: str = "default"


@dataclass
class ApprovalRecord:
    """Bản ghi phê duyệt Human-In-The-Loop (HITL) Gate 1 hoặc Gate 2."""

    id: str
    user_id: str
    symbol: str
    gate: str = "gate1"
    status: str = "pending"  # pending | approved | rejected
    reason: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        """Chuyển đổi bản ghi sang dictionary phục vụ JSON serialization."""
        return {
            "id": self.id,
            "approval_id": self.id,
            "user_id": self.user_id,
            "symbol": self.symbol,
            "gate": self.gate,
            "status": self.status,
            "reason": self.reason,
            "payload": self.payload,
        }


@dataclass
class RunRecord:
    """Lưu trữ dữ liệu một lần thực thi Chat hoặc Scan (One-shot steps) trong bộ nhớ."""

    id: str
    kind: str  # chat | scan
    user_id: str
    steps: list[dict[str, Any]] = field(default_factory=list)
    result: dict[str, Any] = field(default_factory=dict)


@dataclass
class LastQuoteRecord:
    """Giá và trạng thái định tuyến gần nhất phục vụ Market status."""

    symbol: str
    user_id: str = "default"
    price: float | None = None
    change_pct: float | None = None
    route: str = ""
    updated_at: str = ""


def default_db_path() -> str:
    """Đường dẫn tệp SQLite lưu trữ dữ liệu backend store (ưu tiên root resources/data/)."""
    root_default = Path(__file__).resolve().parents[2] / "resources" / "data" / "backend_store.db"
    return os.environ.get("BACKEND_SQLITE_PATH", str(root_default))


def _connect(db_path: str) -> sqlite3.Connection:
    """Khởi tạo kết nối SQLite và tạo các bảng cần thiết nếu chưa tồn tại."""
    path = Path(db_path)
    if str(path) != ":memory:":
        path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS watchlist (
            user_id TEXT NOT NULL,
            symbol TEXT NOT NULL,
            threshold_pct REAL NOT NULL CHECK (threshold_pct > 0),
            PRIMARY KEY (user_id, symbol)
        );
        CREATE TABLE IF NOT EXISTS approvals (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            symbol TEXT NOT NULL,
            gate TEXT NOT NULL DEFAULT 'gate1',
            status TEXT NOT NULL DEFAULT 'pending',
            reason TEXT,
            payload_json TEXT NOT NULL DEFAULT '{}'
        );
        CREATE TABLE IF NOT EXISTS last_quotes (
            user_id TEXT NOT NULL,
            symbol TEXT NOT NULL,
            price REAL,
            change_pct REAL,
            route TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL,
            PRIMARY KEY (user_id, symbol)
        );
        """
    )
    conn.commit()
    return conn


class Store:
    """Kho lưu trữ dữ liệu tập trung cho Backend (Watchlist, Approvals, Last Quotes, Runs)."""

    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = db_path if db_path is not None else default_db_path()
        self._lock = threading.Lock()
        self._conn = _connect(self.db_path)
        self._runs: dict[str, RunRecord] = {}

    def clear(self) -> None:
        """Xóa toàn bộ dữ liệu watchlist, approvals, last_quotes và runs (dùng cho unit tests)."""
        with self._lock:
            self._conn.execute("DELETE FROM watchlist")
            self._conn.execute("DELETE FROM approvals")
            self._conn.execute("DELETE FROM last_quotes")
            self._conn.commit()
            self._runs.clear()

    def save_run(self, run: RunRecord) -> RunRecord:
        """Lưu lại bản ghi lần chạy (run)."""
        with self._lock:
            self._runs[run.id] = run
            return run

    def get_run(self, run_id: str) -> RunRecord | None:
        """Lấy bản ghi lần chạy theo run_id."""
        with self._lock:
            return self._runs.get(run_id)

    def list_watchlist(self, user_id: str = "default") -> list[WatchlistItem]:
        """Liệt kê danh sách mã cổ phiếu trong watchlist của người dùng."""
        with self._lock:
            rows = self._conn.execute(
                "SELECT user_id, symbol, threshold_pct FROM watchlist "
                "WHERE user_id = ? ORDER BY symbol",
                (user_id,),
            ).fetchall()
        return [
            WatchlistItem(
                symbol=r["symbol"],
                threshold_pct=float(r["threshold_pct"]),
                user_id=r["user_id"],
            )
            for r in rows
        ]

    def get_watchlist(self, user_id: str, symbol: str) -> WatchlistItem | None:
        """Lấy thông tin một mã cổ phiếu trong watchlist."""
        with self._lock:
            row = self._conn.execute(
                "SELECT user_id, symbol, threshold_pct FROM watchlist "
                "WHERE user_id = ? AND symbol = ?",
                (user_id, symbol.upper()),
            ).fetchone()
        if row is None:
            return None
        return WatchlistItem(
            symbol=row["symbol"],
            threshold_pct=float(row["threshold_pct"]),
            user_id=row["user_id"],
        )

    def upsert_watchlist(self, item: WatchlistItem) -> WatchlistItem:
        """Thêm mới hoặc cập nhật ngưỡng cảnh báo cho mã cổ phiếu."""
        saved = WatchlistItem(
            symbol=item.symbol.upper(),
            threshold_pct=float(item.threshold_pct),
            user_id=item.user_id or "default",
        )
        with self._lock:
            self._conn.execute(
                "INSERT INTO watchlist (user_id, symbol, threshold_pct) "
                "VALUES (?, ?, ?) "
                "ON CONFLICT(user_id, symbol) DO UPDATE SET "
                "threshold_pct = excluded.threshold_pct",
                (saved.user_id, saved.symbol, saved.threshold_pct),
            )
            self._conn.commit()
        return saved

    def delete_watchlist(self, user_id: str, symbol: str) -> bool:
        """Xóa mã cổ phiếu khỏi danh mục theo dõi."""
        with self._lock:
            cur = self._conn.execute(
                "DELETE FROM watchlist WHERE user_id = ? AND symbol = ?",
                (user_id, symbol.upper()),
            )
            self._conn.commit()
            return cur.rowcount > 0

    def upsert_last_quote(self, rec: LastQuoteRecord) -> LastQuoteRecord:
        """Cập nhật giá và trạng thái quét gần nhất của mã cổ phiếu."""
        saved = LastQuoteRecord(
            symbol=rec.symbol.upper(),
            user_id=rec.user_id or "default",
            price=rec.price,
            change_pct=rec.change_pct,
            route=rec.route or "",
            updated_at=rec.updated_at or "",
        )
        with self._lock:
            self._conn.execute(
                "INSERT INTO last_quotes "
                "(user_id, symbol, price, change_pct, route, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(user_id, symbol) DO UPDATE SET "
                "price = excluded.price, change_pct = excluded.change_pct, "
                "route = excluded.route, updated_at = excluded.updated_at",
                (
                    saved.user_id,
                    saved.symbol,
                    saved.price,
                    saved.change_pct,
                    saved.route,
                    saved.updated_at,
                ),
            )
            self._conn.commit()
        return saved

    def get_last_quote(self, user_id: str, symbol: str) -> LastQuoteRecord | None:
        """Lấy giá và trạng thái quét gần nhất của mã cổ phiếu."""
        with self._lock:
            row = self._conn.execute(
                "SELECT user_id, symbol, price, change_pct, route, updated_at "
                "FROM last_quotes WHERE user_id = ? AND symbol = ?",
                (user_id, symbol.upper()),
            ).fetchone()
        if row is None:
            return None
        return LastQuoteRecord(
            symbol=row["symbol"],
            user_id=row["user_id"],
            price=row["price"],
            change_pct=row["change_pct"],
            route=row["route"] or "",
            updated_at=row["updated_at"] or "",
        )

    def get_approval(self, approval_id: str) -> ApprovalRecord | None:
        """Lấy thông tin bản ghi phê duyệt theo id."""
        with self._lock:
            row = self._conn.execute(
                "SELECT id, user_id, symbol, gate, status, reason, payload_json "
                "FROM approvals WHERE id = ?",
                (approval_id,),
            ).fetchone()
        return _row_to_approval(row) if row else None

    def explain_approval_failure(
        self, approval_id: str, user_id: str = "default"
    ) -> str:
        """Mô tả chi tiết nguyên nhân khi thao tác approve/reject thất bại."""
        aid = (approval_id or "").strip()
        if not aid:
            return "approval_id rỗng"
        rec = self.get_approval(aid)
        if rec is None or rec.user_id != user_id:
            return "không tìm thấy approval"
        if rec.status != "pending":
            return f"approval đã xử lý (status={rec.status})"
        return "không thể xử lý approval"

    def list_pending(self, user_id: str = "default") -> list[ApprovalRecord]:
        """Liệt kê danh sách các bản ghi đang chờ phê duyệt (status='pending')."""
        with self._lock:
            rows = self._conn.execute(
                "SELECT id, user_id, symbol, gate, status, reason, payload_json "
                "FROM approvals WHERE user_id = ? AND status = 'pending' "
                "ORDER BY id",
                (user_id,),
            ).fetchall()
        return [_row_to_approval(r) for r in rows]

    def add_pending(self, rec: ApprovalRecord) -> ApprovalRecord:
        """Thêm mới một yêu cầu phê duyệt vào hàng đợi."""
        with self._lock:
            existing = self._conn.execute(
                "SELECT id, user_id, symbol, gate, status, reason, payload_json "
                "FROM approvals WHERE id = ?",
                (rec.id,),
            ).fetchone()
            if existing is not None and existing["status"] != "pending":
                return _row_to_approval(existing)
            payload = json.dumps(rec.payload or {}, ensure_ascii=False)
            if existing is None:
                self._conn.execute(
                    "INSERT INTO approvals "
                    "(id, user_id, symbol, gate, status, reason, payload_json) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        rec.id,
                        rec.user_id,
                        rec.symbol,
                        rec.gate,
                        rec.status or "pending",
                        rec.reason,
                        payload,
                    ),
                )
            else:
                self._conn.execute(
                    "UPDATE approvals SET user_id=?, symbol=?, gate=?, "
                    "status=?, reason=?, payload_json=? WHERE id=?",
                    (
                        rec.user_id,
                        rec.symbol,
                        rec.gate,
                        rec.status or "pending",
                        rec.reason,
                        payload,
                        rec.id,
                    ),
                )
            self._conn.commit()
            row = self._conn.execute(
                "SELECT id, user_id, symbol, gate, status, reason, payload_json "
                "FROM approvals WHERE id = ?",
                (rec.id,),
            ).fetchone()
        return _row_to_approval(row) if row else rec

    def approve(
        self, approval_id: str, user_id: str = "default"
    ) -> ApprovalRecord | None:
        """Phê duyệt yêu cầu (chuyển status thành 'approved')."""
        with self._lock:
            row = self._conn.execute(
                "SELECT id, user_id, symbol, gate, status, reason, payload_json "
                "FROM approvals WHERE id = ?",
                (approval_id,),
            ).fetchone()
            if (
                row is None
                or row["user_id"] != user_id
                or row["status"] != "pending"
            ):
                return None
            self._conn.execute(
                "UPDATE approvals SET status = 'approved' WHERE id = ?",
                (approval_id,),
            )
            self._conn.commit()
            row = self._conn.execute(
                "SELECT id, user_id, symbol, gate, status, reason, payload_json "
                "FROM approvals WHERE id = ?",
                (approval_id,),
            ).fetchone()
        return _row_to_approval(row) if row else None

    def reject(
        self, approval_id: str, *, reason: str, user_id: str = "default"
    ) -> ApprovalRecord | None:
        """Từ chối yêu cầu (chuyển status thành 'rejected' kèm lý do)."""
        with self._lock:
            row = self._conn.execute(
                "SELECT id, user_id, symbol, gate, status, reason, payload_json "
                "FROM approvals WHERE id = ?",
                (approval_id,),
            ).fetchone()
            if (
                row is None
                or row["user_id"] != user_id
                or row["status"] != "pending"
            ):
                return None
            self._conn.execute(
                "UPDATE approvals SET status = 'rejected', reason = ? WHERE id = ?",
                (reason, approval_id),
            )
            self._conn.commit()
            row = self._conn.execute(
                "SELECT id, user_id, symbol, gate, status, reason, payload_json "
                "FROM approvals WHERE id = ?",
                (approval_id,),
            ).fetchone()
        return _row_to_approval(row) if row else None


def _row_to_approval(row: sqlite3.Row) -> ApprovalRecord:
    payload: dict[str, Any] = {}
    raw = row["payload_json"] or "{}"
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            payload = parsed
    except json.JSONDecodeError:
        payload = {}
    return ApprovalRecord(
        id=row["id"],
        user_id=row["user_id"],
        symbol=row["symbol"],
        gate=row["gate"],
        status=row["status"],
        reason=row["reason"],
        payload=payload,
    )
