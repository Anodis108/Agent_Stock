"""Nodes db_agent — hàm thuần: nhận DBState, trả partial dict.

ĐỌC lịch sử giá + tin (tự động). SOẠN lệnh ghi cho tin/giá ứng viên chưa có
trong kho (soạn ≠ commit). COMMIT qua `approve_pending_write` — hub gọi sau
`interrupt_before=["hitl_commit"]`. Không LLM.

Gọi trực tiếp bởi tool (tools.py), không phải node trong 1 graph tuyến tính:
- `read_symbol_store` → `read` rồi `parse`.
- `stage_new_rows` → `read` → `stage_writes` → `parse`.
`normalize` không nằm trong 2 luồng trên (tool tự upper/strip mã) nhưng vẫn
export để test đơn lẻ (tests/test_db_agent.py::test_ma_sai).
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path

from app.agent_pr.db_agent.schemas import Agent_Output, PendingWrite, PriceRow, SavedNews
from app.agent_pr.db_agent.state import DBState
from app.monitoring.tracing import step_parent, trace_step

_DB_PATH = Path(__file__).resolve().parents[3] / "data" / "agent_pr.sqlite3"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    trading_date TEXT NOT NULL,
    close REAL NOT NULL,
    ts REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_prices_symbol_ts ON prices(symbol, ts);

CREATE TABLE IF NOT EXISTS news (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    ts REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_news_symbol_ts ON news(symbol, ts);

CREATE TABLE IF NOT EXISTS news_pending (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending'
);

CREATE TABLE IF NOT EXISTS price_pending (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    trading_date TEXT NOT NULL,
    close REAL NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending'
);
"""

_UNIQUE_INDEXES = """
CREATE UNIQUE INDEX IF NOT EXISTS idx_news_symbol_url ON news(symbol, url);
CREATE UNIQUE INDEX IF NOT EXISTS idx_news_pending_symbol_url ON news_pending(symbol, url);
CREATE UNIQUE INDEX IF NOT EXISTS idx_prices_symbol_date ON prices(symbol, trading_date);
CREATE UNIQUE INDEX IF NOT EXISTS idx_price_pending_symbol_date
    ON price_pending(symbol, trading_date);
"""


def _connect() -> sqlite3.Connection:
    """Mở connection sqlite, tạo schema nếu chưa có, đảm bảo unique index rồi trả về.

    Gọi lại mỗi lần cần DB (không giữ connection global) — sqlite file nhỏ,
    connect rẻ hơn lo thread-safety của 1 connection dùng chung.
    """
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    _ensure_unique_keys(conn)
    return conn


def _ensure_unique_keys(conn: sqlite3.Connection) -> None:
    """Migration một lần: thêm UNIQUE index (symbol, url/date) cho DB tạo trước khi có ràng buộc này.

    Trước khi có unique index, INSERT OR IGNORE không chặn được trùng lặp nên
    DB cũ có thể có bản ghi trùng (symbol, url)/(symbol, trading_date) — phải
    xoá bớt (giữ id nhỏ nhất) rồi mới tạo được UNIQUE index. Idempotent: kiểm
    tra index đã tồn tại (dòng đầu) để bỏ qua bước dọn dẹp ở các lần gọi sau.
    """
    have = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'index' AND name = 'idx_news_symbol_url'"
    ).fetchone()
    if have:
        conn.executescript(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_prices_symbol_date "
            "ON prices(symbol, trading_date);"
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_price_pending_symbol_date "
            "ON price_pending(symbol, trading_date);"
        )
        return
    conn.execute(
        "DELETE FROM news WHERE id NOT IN (SELECT MIN(id) FROM news GROUP BY symbol, url)"
    )
    conn.execute(
        "DELETE FROM news_pending WHERE id NOT IN "
        "(SELECT MIN(id) FROM news_pending GROUP BY symbol, url)"
    )
    conn.executescript(_UNIQUE_INDEXES)


def normalize(state: DBState) -> dict:
    """Upper + strip mã — hàm thuần, không dùng trong graph ReAct (tools.py tự normalize
    inline) nhưng vẫn export để test đơn lẻ (xem tests/test_db_agent.py::test_ma_sai)."""
    with trace_step(step_parent(state, "db_agent"), "db_normalize", input=state.get("symbol", "")) as t:
        symbol = str(state.get("symbol") or "").strip().upper()
        t["output"] = symbol
        return {"symbol": symbol}


def read(state: DBState) -> dict:
    """Đọc tối đa 5 phiên giá + toàn bộ tin đã lưu cho `symbol` — gọi bởi tool `read_symbol_store`."""
    symbol = state["symbol"]
    with trace_step(step_parent(state, "db_agent"), "db_read", input=symbol) as t:
        out = _read_rows(symbol)
        t["output"] = {
            "n_price": len(out["price_rows"]),
            "n_news": len(out["news_rows"]),
        }
        return out


def _read_rows(symbol: str) -> dict:
    """Query thuần sqlite, không trace_step riêng — `read` đã bọc span cho cả 2 câu SELECT."""
    with _connect() as conn:
        price_cur = conn.execute(
            "SELECT trading_date, close FROM prices WHERE symbol = ? "
            "ORDER BY ts DESC LIMIT 5",
            (symbol,),
        )
        news_cur = conn.execute(
            "SELECT title, url FROM news WHERE symbol = ? ORDER BY ts DESC",
            (symbol,),
        )
        price_rows = [dict(row) for row in price_cur.fetchall()]
        news_rows = [dict(row) for row in news_cur.fetchall()]
    return {"price_rows": price_rows, "news_rows": news_rows}


def stage_writes(state: DBState) -> dict:
    """Soạn (không commit) lệnh ghi cho tin/giá ứng viên chưa có trong bảng chính.

    Gọi bởi tool `stage_new_rows` sau khi crawl xong — kết quả nằm ở bảng
    `*_pending`, chờ `approve_pending_write` (hub HITL) COMMIT vào `news`/`prices`.
    """
    symbol = state["symbol"]
    news_cands = state.get("candidate_news") or []
    price_cands = state.get("candidate_prices") or []
    with trace_step(step_parent(state, "db_agent"), "db_stage_writes", input=symbol) as t:
        pending_rows = _stage_pending(symbol, news_cands) + _stage_prices(symbol, price_cands)
        t["output"] = {"n_pending": len(pending_rows)}
        return {"pending_rows": pending_rows}


def _item_url(item) -> str:
    """Đọc `.url` dù `item` là Pydantic model (CandidateNews) hay dict thô."""
    return item.url if hasattr(item, "url") else item.get("url", "")


def _item_title(item) -> str:
    """Đọc `.title` dù `item` là Pydantic model hay dict thô."""
    return item.title if hasattr(item, "title") else item.get("title", "")


def _stage_pending(symbol: str, candidates) -> list[dict]:
    """Soạn pending cho tin ứng viên — bỏ qua tin đã có trong `news` (chính thức)
    hoặc trùng URL trong cùng batch. Tin từng bị `rejected` mà bị crawl lại thì
    được đưa về `pending` (cho phép duyệt lại) thay vì bỏ qua vĩnh viễn."""
    with _connect() as conn:
        official = {
            row["url"]
            for row in conn.execute(
                "SELECT url FROM news WHERE symbol = ?",
                (symbol,),
            ).fetchall()
        }
        pending_rows: list[dict] = []
        seen_this_batch: set[str] = set()
        for item in candidates:
            url = _item_url(item)
            title = _item_title(item)
            if not url or url in official or url in seen_this_batch:
                continue
            seen_this_batch.add(url)
            conn.execute(
                "INSERT OR IGNORE INTO news_pending (symbol, title, url, status) "
                "VALUES (?, ?, ?, 'pending')",
                (symbol, title, url),
            )
            row = conn.execute(
                "SELECT id, symbol, title, url, status FROM news_pending "
                "WHERE symbol = ? AND url = ?",
                (symbol, url),
            ).fetchone()
            if row is None or row["status"] == "approved":
                continue
            if row["status"] == "rejected":
                conn.execute(
                    "UPDATE news_pending SET title = ?, status = 'pending' WHERE id = ?",
                    (title, row["id"]),
                )
                pending_rows.append(
                    {
                        "id": row["id"],
                        "symbol": symbol,
                        "title": title,
                        "url": url,
                        "kind": "news",
                    }
                )
                continue
            pending_rows.append(
                {
                    "id": row["id"],
                    "symbol": row["symbol"],
                    "title": row["title"],
                    "url": row["url"],
                    "kind": "news",
                }
            )
    return pending_rows


def _price_date(item) -> str:
    """Đọc `.trading_date` dù `item` là Pydantic model (CandidatePrice) hay dict thô."""
    return item.trading_date if hasattr(item, "trading_date") else item.get("trading_date", "")


def _price_close(item) -> float:
    """Đọc `.close` dù `item` là Pydantic model hay dict thô; thiếu/0 → 0.0 (loại bỏ ở caller)."""
    return float(item.close if hasattr(item, "close") else item.get("close") or 0)


def _stage_prices(symbol: str, candidates) -> list[dict]:
    """Soạn pending cho giá ứng viên — bỏ qua ngày đã có trong `prices` (chính
    thức), ngày trùng trong cùng batch, hoặc `close <= 0` (dữ liệu hỏng)."""
    with _connect() as conn:
        official = {
            row["trading_date"]
            for row in conn.execute(
                "SELECT trading_date FROM prices WHERE symbol = ?",
                (symbol,),
            ).fetchall()
        }
        pending_rows: list[dict] = []
        seen: set[str] = set()
        for item in candidates:
            date = str(_price_date(item) or "").strip()
            close = _price_close(item)
            if not date or close <= 0 or date in official or date in seen:
                continue
            seen.add(date)
            conn.execute(
                "INSERT OR IGNORE INTO price_pending "
                "(symbol, trading_date, close, status) VALUES (?, ?, ?, 'pending')",
                (symbol, date, close),
            )
            row = conn.execute(
                "SELECT id, symbol, trading_date, close, status FROM price_pending "
                "WHERE symbol = ? AND trading_date = ?",
                (symbol, date),
            ).fetchone()
            if row is None or row["status"] == "approved":
                continue
            if row["status"] == "rejected":
                conn.execute(
                    "UPDATE price_pending SET close = ?, status = 'pending' WHERE id = ?",
                    (close, row["id"]),
                )
            title = f"Giá đóng cửa {date}: {close:,.0f} VND"
            pending_rows.append(
                {
                    "id": row["id"],
                    "symbol": symbol,
                    "title": title,
                    "url": "",
                    "kind": "price",
                    "trading_date": date,
                    "close": close,
                }
            )
    return pending_rows


def parse(state: DBState) -> dict:
    """rows đã đọc + pending vừa soạn → Agent_Output. Field `result` là output graph."""
    symbol = state["symbol"]
    price_rows = state.get("price_rows") or []
    news_rows = state.get("news_rows") or []
    pending_rows = state.get("pending_rows") or []
    with trace_step(step_parent(state, "db_agent"), "db_parse", input=symbol) as t:
        pending = [PendingWrite(**_pending_fields(row)) for row in pending_rows]
        result = Agent_Output(
            symbol=symbol,
            price_history=[PriceRow(**row) for row in price_rows],
            saved_news=[SavedNews(**row) for row in news_rows],
            pending_writes=pending,
            detail=(
                f"đọc {len(price_rows)} phiên giá + {len(news_rows)} tin đã lưu · "
                f"soạn {len(pending)} lệnh ghi mới (chờ HITL ở hub)"
                if pending
                else (
                    f"đọc {len(price_rows)} phiên giá + {len(news_rows)} tin đã lưu"
                    + (
                        " — đủ dùng, không cần crawl"
                        if price_rows or news_rows
                        else " — chưa có dữ liệu"
                    )
                )
            ),
        )
        t["output"] = result.detail
        return {"result": result}


def _pending_fields(row: dict) -> dict:
    """Chuẩn hoá 1 dict pending (từ `_stage_pending`/`_stage_prices`) thành kwargs cho `PendingWrite`."""
    return {
        "id": int(row["id"]),
        "symbol": str(row.get("symbol") or ""),
        "title": str(row.get("title") or ""),
        "url": str(row.get("url") or ""),
        "kind": str(row.get("kind") or "news"),
        "trading_date": str(row.get("trading_date") or ""),
        "close": row.get("close"),
    }


def approve_pending_write(pending_id: int, *, approve: bool, kind: str = "news") -> bool:
    """Duyệt / từ chối 1 lệnh đang treo. Idempotent theo (kind, pending_id)."""
    if kind == "price":
        return _approve_price(pending_id, approve)
    return _approve_news(pending_id, approve)


def _approve_news(pending_id: int, approve: bool) -> bool:
    """COMMIT/reject 1 tin pending. Idempotent: nếu đã quyết định trước đó (khác
    `pending`), trả lại đúng kết quả tương ứng thay vì ghi đè lần quyết định cũ."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT symbol, title, url, status FROM news_pending WHERE id = ?",
            (pending_id,),
        ).fetchone()
        if row is None:
            return False
        if row["status"] != "pending":
            return (row["status"] == "approved") is approve
        if approve:
            conn.execute(
                "INSERT OR IGNORE INTO news (symbol, title, url, ts) VALUES (?, ?, ?, ?)",
                (row["symbol"], row["title"], row["url"], time.time()),
            )
            conn.execute(
                "UPDATE news_pending SET status = 'approved' WHERE id = ?",
                (pending_id,),
            )
        else:
            conn.execute(
                "UPDATE news_pending SET status = 'rejected' WHERE id = ?",
                (pending_id,),
            )
    return True


def _approve_price(pending_id: int, approve: bool) -> bool:
    """COMMIT/reject 1 giá pending — cùng logic idempotent với `_approve_news`."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT symbol, trading_date, close, status FROM price_pending WHERE id = ?",
            (pending_id,),
        ).fetchone()
        if row is None:
            return False
        if row["status"] != "pending":
            return (row["status"] == "approved") is approve
        if approve:
            conn.execute(
                "INSERT OR IGNORE INTO prices (symbol, trading_date, close, ts) "
                "VALUES (?, ?, ?, ?)",
                (row["symbol"], row["trading_date"], row["close"], time.time()),
            )
            conn.execute(
                "UPDATE price_pending SET status = 'approved' WHERE id = ?",
                (pending_id,),
            )
        else:
            conn.execute(
                "UPDATE price_pending SET status = 'rejected' WHERE id = ?",
                (pending_id,),
            )
    return True
