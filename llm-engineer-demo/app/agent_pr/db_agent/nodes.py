"""Nodes db_agent — 4 hàm thuần: nhận DBState, trả partial dict.

LangGraph chỉ lo thứ tự. Việc thật nằm đây: normalize mã, ĐỌC lịch sử giá +
tin đã lưu (sqlite3, tự động — không HITL), rồi SOẠN lệnh ghi cho tin ứng
viên chưa có trong DB (cũng tự động — soạn ≠ ghi). Không LLM.

sqlite3 mô phỏng tối giản `SinkStore` bên vn-stock-swarm/src/sink_store.py:
3 bảng (prices/news/news_pending) nhưng gói gọn 1 file, đủ cho demo agent_pr.
Kết nối mở/đóng ngay trong từng hàm (không giữ connection sống xuyên node) —
sqlite3 rẻ để mở, và tránh phải quản lý lifecycle qua LangGraph state.

Mọi thao tác CÓ SIDE EFFECT (INSERT/UPDATE `news` / `news_pending`) phải
idempotent: gọi lại cùng (symbol, url) hoặc cùng `pending_id` không nhân bản
hàng. Khóa tự nhiên `(symbol, url)` = idempotency_key (ý plan.md / agent_m2).
ĐỌC không đổi trạng thái — không cần khóa.
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path

from app.agent_pr.db_agent.schemas import Agent_Output, PendingWrite, PriceRow, SavedNews
from app.agent_pr.db_agent.state import DBState
from app.agent_pr.symbol import normalize_symbol
from app.monitoring.tracing import trace_step

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
-- UNIQUE(symbol, url) gắn ở _ensure_unique_keys: approve 2 lần không nhân hàng.
CREATE TABLE IF NOT EXISTS news (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    ts REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_news_symbol_ts ON news(symbol, ts);

-- Lệnh ghi đang treo — soạn ở node stage_writes, commit ở approve_pending_write().
-- status: pending | approved | rejected. Không DELETE sau duyệt — retry cùng
-- pending_id đọc lại quyết định cũ (idempotent) thay vì "không tìm thấy".
-- UNIQUE(symbol, url): stage 2 lần cùng tin → 1 hàng, cùng id.
CREATE TABLE IF NOT EXISTS news_pending (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending'
);
"""

# File DB cũ tạo trước UNIQUE vẫn sống vì CREATE TABLE IF NOT EXISTS — index
# tách khỏi CREATE TABLE để gắn được lên schema đã có, không recreate bảng.
_UNIQUE_INDEXES = """
CREATE UNIQUE INDEX IF NOT EXISTS idx_news_symbol_url ON news(symbol, url);
CREATE UNIQUE INDEX IF NOT EXISTS idx_news_pending_symbol_url ON news_pending(symbol, url);
"""


def _connect() -> sqlite3.Connection:
    """Mở kết nối + đảm bảo schema tồn tại. Gọi trong từng hàm — sqlite3 rẻ
    để mở, và tránh giữ connection sống xuyên node/graph."""
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    _ensure_unique_keys(conn)
    return conn


def _ensure_unique_keys(conn: sqlite3.Connection) -> None:
    """Gắn UNIQUE(symbol, url) — idempotency_key của mọi ghi tin.

    Chỉ dedup khi index chưa có: lần kết nối sau không ghi gì thêm (ĐỌC không
    được có side effect). File bẩn từ bản cũ (cùng url 2 hàng) phải gộp trước
    khi CREATE UNIQUE, không thì sqlite raise.
    """
    have = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'index' AND name = 'idx_news_symbol_url'"
    ).fetchone()
    if have:
        return
    conn.execute(
        "DELETE FROM news WHERE id NOT IN (SELECT MIN(id) FROM news GROUP BY symbol, url)"
    )
    conn.execute(
        "DELETE FROM news_pending WHERE id NOT IN "
        "(SELECT MIN(id) FROM news_pending GROUP BY symbol, url)"
    )
    conn.executescript(_UNIQUE_INDEXES)


# ── Chuẩn hoá mã ──────────────────────────────────────────────────────────────


def normalize(state: DBState) -> dict:
    """Upper + strip; raise ValueError nếu không giống mã niêm yết."""
    with trace_step(state.get("_trace_span"), "db_normalize", input=state.get("symbol", "")) as t:
        symbol = normalize_symbol(str(state.get("symbol") or ""))
        t["output"] = symbol
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
    with trace_step(state.get("_trace_span"), "db_read", input=symbol) as t:
        out = _read_rows(symbol)
        t["output"] = {
            "n_price": len(out["price_rows"]),
            "n_news": len(out["news_rows"]),
        }
        return out


def _read_rows(symbol: str) -> dict:
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

    Idempotent: cùng (symbol, url) gọi lại (hub retry, News+Eval đề xuất trùng)
    không INSERT hàng mới — trả đúng `id` đang treo. Khóa UNIQUE + INSERT OR
    IGNORE, không chỉ set in-memory (set cũ trượt nếu 2 process/2 lượt graph).
    """
    symbol = state["symbol"]
    candidates = state.get("candidate_news") or []
    with trace_step(state.get("_trace_span"), "db_stage_writes", input=symbol) as t:
        if not candidates:
            t["output"] = {"n_pending": 0}
            return {"pending_rows": []}

        pending_rows = _stage_pending(symbol, candidates)
        t["output"] = {"n_pending": len(pending_rows)}
        return {"pending_rows": pending_rows}


def _stage_pending(symbol: str, candidates) -> list[dict]:
    """1 tin = 1 hàng pending. Retry / trùng url trong batch → cùng id.

    - Đã có trong `news` (đã duyệt) → bỏ, không soạn lại.
    - `news_pending` status=pending → trả hàng cũ (already_done).
    - status=rejected → mở lại vòng HITL (UPDATE về pending, giữ id).
    - status=approved → bỏ (đai an toàn nếu hàng `news` lệch).
    """
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
            url = item.url if hasattr(item, "url") else item.get("url", "")
            title = item.title if hasattr(item, "title") else item.get("title", "")
            if not url or url in official or url in seen_this_batch:
                continue
            seen_this_batch.add(url)

            # OR IGNORE: race / retry đụng UNIQUE → 0 hàng mới, SELECT lấy id cũ.
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
                # Từ chối ≠ cấm mãi: crawl sau được đề xuất lại, cùng pending_id.
                conn.execute(
                    "UPDATE news_pending SET title = ?, status = 'pending' WHERE id = ?",
                    (title, row["id"]),
                )
                pending_rows.append(
                    {"id": row["id"], "symbol": symbol, "title": title, "url": url}
                )
                continue
            pending_rows.append(
                {
                    "id": row["id"],
                    "symbol": row["symbol"],
                    "title": row["title"],
                    "url": row["url"],
                }
            )
    return pending_rows


# ── Parse ─────────────────────────────────────────────────────────────────────


def parse(state: DBState) -> dict:
    """price_rows/news_rows/pending_rows → Agent_Output. Field `result` là output graph."""
    symbol = state["symbol"]
    price_rows = state.get("price_rows") or []
    news_rows = state.get("news_rows") or []
    pending_rows = state.get("pending_rows") or []
    with trace_step(state.get("_trace_span"), "db_parse", input=symbol) as t:
        result = Agent_Output(
            symbol=symbol,
            price_history=[PriceRow(**row) for row in price_rows],
            saved_news=[SavedNews(**row) for row in news_rows],
            pending_writes=[PendingWrite(**row) for row in pending_rows],
            detail=(
                f"đọc {len(price_rows)} phiên giá + {len(news_rows)} tin đã lưu (tự động) · "
                f"soạn {len(pending_rows)} lệnh ghi mới (chờ duyệt)"
            ),
        )
        t["output"] = result.detail
        return {"result": result}


# ── HITL — nằm NGOÀI graph, gọi sau khi người duyệt ─────────────────────────
#
# Không phải node: graph db_agent chỉ làm phần tự động (đọc + soạn). Commit
# đòi hỏi 1 quyết định của người, đến ở 1 lời gọi HTTP riêng (giống POST
# /approve bên vn-stock-swarm/src/query/api.py) — nhét vào graph tuyến tính sẽ
# biến "chờ người" thành 1 bước graph phải treo, không hợp với StateGraph ở
# đây (không có interrupt/checkpointer như app/agent).
#
# Side effect (ghi `news` / đổi status) idempotent — xem docstring hàm.


def approve_pending_write(pending_id: int, *, approve: bool) -> bool:
    """Duyệt / từ chối 1 lệnh đang treo. Idempotent theo `pending_id`.

    Duyệt lần đầu: INSERT OR IGNORE `news` (UNIQUE chặn nhân bản nếu commit
    xong mà crash trước khi đổi status), rồi `status='approved'`. Từ chối:
    chỉ `status='rejected'`, không đụng `news`. Không DELETE — gọi lại cùng
    id + cùng quyết định trả True (already_done); đảo quyết định trả False,
    không undo hàng đã ghi. Id không tồn tại → False.
    """
    with _connect() as conn:
        row = conn.execute(
            "SELECT symbol, title, url, status FROM news_pending WHERE id = ?",
            (pending_id,),
        ).fetchone()
        if row is None:
            return False

        # Đã chốt trước đó: cùng chiều = success; ngược chiều = không đảo.
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
