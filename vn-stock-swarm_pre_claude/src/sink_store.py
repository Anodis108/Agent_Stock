"""Kho lưu trữ có thể truy vấn cho 3 đích của SinkRouter (giá / tin theo mã /
tin chung).

Dùng SQLite thay vì JSONL append-only của ResultStore: QueryCoordinator (và 5
agent tầng Hierarchical của nó) cần hỏi được "giá HPG mới nhất cách đây bao
lâu?" và "có tin trong 2 giờ gần đây không?" — điều 1 log chỉ-ghi-thêm không
trả lời được nếu không quét toàn bộ. sqlite3 chạy đồng bộ, nên mọi lệnh gọi
đều được đẩy qua asyncio.to_thread để không chặn event loop (event loop này
còn phải chạy vòng lặp crawl/gossip của agent).

Bảng `news` là kho tin ĐÃ DUYỆT — DBAgent (query/agents/db_agent.py) và mọi
agent Hierarchical khác coi đây là "sự thật" chính thức. Tin theo mã crawl
được ở tầng Swarm (Sơ đồ 1&2, qua SinkRouter) không được ghi thẳng vào đây
nữa — chúng vào `news_pending` trước (xem `save_news_pending`), và chỉ được
"thăng cấp" (`promote_pending_news`) sang `news` sau khi DBAgent thực sự
commit, tức là sau khi HITL duyệt (`POST /approve`, xem query/api.py). Nếu
tin theo mã được ghi thẳng vào `news` ngay lúc crawl như giá, HITL sẽ không
bao giờ có gì để duyệt — mâu thuẫn với chính mục đích tồn tại của nó.
"""

from __future__ import annotations

import asyncio
import json
import sqlite3
import time
from collections.abc import Mapping
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    url TEXT NOT NULL,
    data_json TEXT NOT NULL,
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

-- Tin theo mã crawl được nhưng CHƯA qua HITL — xem docstring module.
CREATE TABLE IF NOT EXISTS news_pending (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    ts REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_news_pending_symbol_ts ON news_pending(symbol, ts);

CREATE TABLE IF NOT EXISTS news_general (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    ts REAL NOT NULL
);
"""


class SinkStore:
    def __init__(self, path: str) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    async def save_price(self, symbol: str, url: str, data: Mapping[str, object]) -> None:
        await asyncio.to_thread(self._save_price_sync, symbol, url, data, time.time())

    def _save_price_sync(
        self, symbol: str, url: str, data: Mapping[str, object], ts: float
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO prices (symbol, url, data_json, ts) VALUES (?, ?, ?, ?)",
                (symbol, url, json.dumps(data, ensure_ascii=False), ts),
            )

    async def save_news(self, symbols: list[str], title: str, url: str) -> None:
        await asyncio.to_thread(self._save_news_sync, symbols, title, url, time.time())

    def _save_news_sync(self, symbols: list[str], title: str, url: str, ts: float) -> None:
        with self._connect() as conn:
            conn.executemany(
                "INSERT INTO news (symbol, title, url, ts) VALUES (?, ?, ?, ?)",
                [(symbol, title, url, ts) for symbol in symbols],
            )

    async def save_news_pending(self, symbols: list[str], title: str, url: str) -> None:
        """Ghi tin theo mã vừa crawl được vào staging — CHƯA phải kho chính
        thức. Gọi bởi SinkRouter (crawl-time) thay vì `save_news` trực tiếp."""
        await asyncio.to_thread(self._save_news_pending_sync, symbols, title, url, time.time())

    def _save_news_pending_sync(
        self, symbols: list[str], title: str, url: str, ts: float
    ) -> None:
        with self._connect() as conn:
            conn.executemany(
                "INSERT INTO news_pending (symbol, title, url, ts) VALUES (?, ?, ?, ?)",
                [(symbol, title, url, ts) for symbol in symbols],
            )

    async def recent_pending_news(
        self, symbol: str, within_seconds: float
    ) -> list[dict[str, object]]:
        """Tin theo mã đã crawl nhưng chưa qua HITL — nguồn NewsAgent đọc để
        báo cáo, và DBAgent đọc để soạn PendingWrite."""
        cutoff = time.time() - within_seconds
        rows = await asyncio.to_thread(self._recent_pending_news_sync, symbol, cutoff)
        return [dict(row) for row in rows]

    def _recent_pending_news_sync(self, symbol: str, cutoff: float) -> list[sqlite3.Row]:
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT symbol, title, url, ts FROM news_pending "
                "WHERE symbol = ? AND ts >= ? ORDER BY ts DESC",
                (symbol, cutoff),
            )
            return cur.fetchall()

    async def has_recent_pending_news(self, symbol: str, within_seconds: float) -> bool:
        pending = await self.recent_pending_news(symbol, within_seconds)
        return len(pending) > 0

    async def promote_pending_news(self, symbols: list[str], title: str, url: str) -> None:
        """HITL đã duyệt — chuyển 1 tin từ staging (`news_pending`) sang kho
        chính thức (`news`). Không xoá khỏi `news_pending` (giữ làm nhật ký
        crawl-time thô); truy vấn "đã lưu chưa" luôn dựa trên bảng `news`."""
        await self.save_news(symbols, title, url)

    async def save_news_general(self, title: str, url: str) -> None:
        await asyncio.to_thread(self._save_news_general_sync, title, url, time.time())

    def _save_news_general_sync(self, title: str, url: str, ts: float) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO news_general (title, url, ts) VALUES (?, ?, ?)", (title, url, ts)
            )

    async def latest_price_age_seconds(self, symbol: str) -> float | None:
        row = await asyncio.to_thread(self._latest_price_sync, symbol)
        if row is None:
            return None
        return time.time() - row["ts"]

    def _latest_price_sync(self, symbol: str) -> sqlite3.Row | None:
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT ts FROM prices WHERE symbol = ? ORDER BY ts DESC LIMIT 1", (symbol,)
            )
            return cur.fetchone()

    async def has_recent_news(self, symbol: str, within_seconds: float) -> bool:
        news = await self.recent_news(symbol, within_seconds)
        return len(news) > 0

    async def recent_news(self, symbol: str, within_seconds: float) -> list[dict[str, object]]:
        cutoff = time.time() - within_seconds
        rows = await asyncio.to_thread(self._recent_news_sync, symbol, cutoff)
        return [dict(row) for row in rows]

    def _recent_news_sync(self, symbol: str, cutoff: float) -> list[sqlite3.Row]:
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT symbol, title, url, ts FROM news "
                "WHERE symbol = ? AND ts >= ? ORDER BY ts DESC",
                (symbol, cutoff),
            )
            return cur.fetchall()

    async def price_history(self, symbol: str, limit: int = 50) -> list[dict[str, object]]:
        rows = await asyncio.to_thread(self._price_history_sync, symbol, limit)
        return [dict(row) for row in rows]

    def _price_history_sync(self, symbol: str, limit: int) -> list[sqlite3.Row]:
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT symbol, url, data_json, ts FROM prices WHERE symbol = ? "
                "ORDER BY ts DESC LIMIT ?",
                (symbol, limit),
            )
            return cur.fetchall()
