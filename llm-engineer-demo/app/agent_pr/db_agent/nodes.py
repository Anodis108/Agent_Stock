"""Nodes db_agent — 4 hàm thuần: nhận DBState, trả partial dict.

LangGraph chỉ lo thứ tự. Việc thật nằm đây: normalize mã, ĐỌC lịch sử giá +
tin đã lưu (sqlite3, tự động — không HITL), rồi SOẠN lệnh ghi cho tin ứng
viên chưa có trong DB (cũng tự động — soạn ≠ ghi). Không LLM.

sqlite3 mô phỏng tối giản `SinkStore` bên vn-stock-swarm/src/sink_store.py:
3 bảng (prices/news/news_pending) nhưng gói gọn 1 file, đủ cho demo agent_pr.
Kết nối mở/đóng ngay trong từng hàm (không giữ connection sống xuyên node) —
sqlite3 rẻ để mở, và tránh phải quản lý lifecycle qua LangGraph state.
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path

from app.agent_pr.db_agent.schemas import Agent_Output, PendingWrite, PriceRow, SavedNews
from app.agent_pr.db_agent.state import DBState

ALLOWED = frozenset({"VNM", "HPG", "FPT", "VCB"})

# File riêng cho slice agent_pr — không đụng DB nào khác trong llm-engineer-demo
# (chưa có DB nào trước db_agent) hay của vn-stock-swarm/src (2 project độc lập).
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

-- Kho tin CHÍNH THỨC — chỉ có bản ghi sau khi approve_pending_write() commit.
CREATE TABLE IF NOT EXISTS news (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    ts REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_news_symbol_ts ON news(symbol, ts);

-- Lệnh ghi đang treo — soạn ở node stage_writes, commit ở approve_pending_write().
CREATE TABLE IF NOT EXISTS news_pending (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending'
);
"""


def _connect() -> sqlite3.Connection:
    """Mở kết nối + đảm bảo schema tồn tại. Gọi trong từng hàm — sqlite3 rẻ
    để mở, và tránh giữ connection sống xuyên node/graph."""
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    return conn


# ── Chuẩn hoá mã ──────────────────────────────────────────────────────────────


def normalize(state: DBState) -> dict:
    """Upper + strip; raise ValueError nếu mã chưa nằm whitelist."""
    symbol = str(state.get("symbol") or "").strip().upper()
    if symbol not in ALLOWED:
        raise ValueError(f"Mã '{symbol}' chưa hỗ trợ")
    return {"symbol": symbol}


# ── ĐỌC — luôn tự động, không HITL ──────────────────────────────────────────
#
# Đọc chỉ là truy vấn, không đổi trạng thái hệ thống — đúng nguyên tắc Sơ đồ 3
# "ĐỌC tự động — không cần người". Không có dữ liệu vẫn trả rows rỗng (không
# raise) — khác craw_agent/news_agent vì "chưa từng ghi gì" là trạng thái hợp
# lệ của 1 mã mới, không phải lỗi.


def read(state: DBState) -> dict:
    """Đọc lịch sử giá + tin đã lưu (bảng CHÍNH THỨC) của 1 mã."""
    symbol = state["symbol"]
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


# ── SOẠN lệnh ghi — tự động soạn, nhưng KHÔNG commit ────────────────────────
#
# Soạn PendingWrite cho tin ứng viên (candidate_news, do NewsAgent tìm được)
# CHƯA có url trong bảng `news` chính thức. Đây là bước ③b "soạn lệnh" của Sơ
# đồ 3 — ghi xuống `news_pending`, không đụng bảng `news`. Commit thật chỉ xảy
# ra qua approve_pending_write(), gọi TÁCH RIÊNG khỏi graph này (xem graph.py).


def stage_writes(state: DBState) -> dict:
    """So candidate_news với url đã có trong `news`; url mới → INSERT news_pending.

    `existing` gộp cả `news` (đã duyệt) lẫn `news_pending` (đang treo, kể cả
    url vừa soạn trong chính vòng lặp này) — tránh soạn 2 PendingWrite trùng
    url nếu candidate_news chứa cùng 1 tin 2 lần (vd NewsAgent + EvalAgent
    cùng đề xuất), giống ý tưởng idempotency_key nhắc trong plan.md.
    """
    symbol = state["symbol"]
    candidates = state.get("candidate_news") or []
    if not candidates:
        return {"pending_rows": []}

    with _connect() as conn:
        existing = {
            row["url"]
            for row in conn.execute(
                "SELECT url FROM news WHERE symbol = ? "
                "UNION SELECT url FROM news_pending WHERE symbol = ? AND status = 'pending'",
                (symbol, symbol),
            ).fetchall()
        }
        pending_rows: list[dict] = []
        for item in candidates:
            url = item.url if hasattr(item, "url") else item.get("url", "")
            title = item.title if hasattr(item, "title") else item.get("title", "")
            if not url or url in existing:
                continue
            cur = conn.execute(
                "INSERT INTO news_pending (symbol, title, url, status) VALUES (?, ?, ?, 'pending')",
                (symbol, title, url),
            )
            pending_rows.append({"id": cur.lastrowid, "symbol": symbol, "title": title, "url": url})
            existing.add(url)
    return {"pending_rows": pending_rows}


# ── Parse ─────────────────────────────────────────────────────────────────────


def parse(state: DBState) -> dict:
    """price_rows/news_rows/pending_rows → Agent_Output. Field `result` là output graph."""
    symbol = state["symbol"]
    price_rows = state.get("price_rows") or []
    news_rows = state.get("news_rows") or []
    pending_rows = state.get("pending_rows") or []
    return {
        "result": Agent_Output(
            symbol=symbol,
            price_history=[PriceRow(**row) for row in price_rows],
            saved_news=[SavedNews(**row) for row in news_rows],
            pending_writes=[PendingWrite(**row) for row in pending_rows],
            detail=(
                f"đọc {len(price_rows)} phiên giá + {len(news_rows)} tin đã lưu (tự động) · "
                f"soạn {len(pending_rows)} lệnh ghi mới (chờ duyệt)"
            ),
        )
    }


# ── HITL — nằm NGOÀI graph, gọi sau khi người duyệt ─────────────────────────
#
# Không phải node: graph db_agent chỉ làm phần tự động (đọc + soạn). Commit
# đòi hỏi 1 quyết định của người, đến ở 1 lời gọi HTTP riêng (giống POST
# /approve bên vn-stock-swarm/src/query/api.py) — nhét vào graph tuyến tính sẽ
# biến "chờ người" thành 1 bước graph phải treo, không hợp với StateGraph ở
# đây (không có interrupt/checkpointer như app/agent).


def approve_pending_write(pending_id: int, *, approve: bool) -> bool:
    """Duyệt (approve=True) → promote sang `news` chính thức, xoá khỏi
    `news_pending`. Từ chối (approve=False) → xoá khỏi `news_pending`, không
    ghi gì vào `news`. Trả False nếu `pending_id` không tồn tại/đã xử lý."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT symbol, title, url FROM news_pending WHERE id = ? AND status = 'pending'",
            (pending_id,),
        ).fetchone()
        if row is None:
            return False
        if approve:
            conn.execute(
                "INSERT INTO news (symbol, title, url, ts) VALUES (?, ?, ?, ?)",
                (row["symbol"], row["title"], row["url"], time.time()),
            )
        conn.execute("DELETE FROM news_pending WHERE id = ?", (pending_id,))
    return True
