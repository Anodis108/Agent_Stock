"""Nodes stat_agent — DB demo SQLite + thực thi SQL read-only.

Bảng `luot_ra_vao` — lượt ra/vào khu vực, đúng ví dụ trong tài liệu ý tưởng
("từ 3h đến 4h có bao nhiêu người vào khu vực"). Tên bảng/cột tiếng Việt
không dấu, dễ agent hiểu đúng khi sinh SQL.
"""

from __future__ import annotations

import random
import re
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path

from app.stat_agent.schemas import QueryResult

_DB_PATH = Path(__file__).resolve().parents[2] / "data" / "agent_stat.sqlite3"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS luot_ra_vao (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    khu_vuc TEXT NOT NULL,
    huong TEXT NOT NULL CHECK (huong IN ('vao', 'ra')),
    nguoi TEXT NOT NULL,
    thoi_gian TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_luot_ra_vao_thoi_gian ON luot_ra_vao(thoi_gian);
CREATE INDEX IF NOT EXISTS idx_luot_ra_vao_khu_vuc ON luot_ra_vao(khu_vuc);
"""

SCHEMA_DESC = """Bảng luot_ra_vao — mỗi dòng là 1 lượt ra/vào khu vực:
  id INTEGER      — khoá chính
  khu_vuc TEXT     — tên khu vực, vd. 'Khu A', 'Khu B', 'Cong chinh'
  huong TEXT       — 'vao' (đi vào) hoặc 'ra' (đi ra)
  nguoi TEXT       — tên/mã người
  thoi_gian TEXT   — thời điểm quét thẻ, định dạng 'YYYY-MM-DD HH:MM:SS'"""

_AREAS = ["Khu A", "Khu B", "Cong chinh", "Kho hang"]
_PEOPLE = [f"NV{i:03d}" for i in range(1, 41)]


def _connect() -> sqlite3.Connection:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    return conn


def ensure_seed_data(n_rows: int = 500) -> int:
    """Sinh dữ liệu mẫu 1 lần nếu bảng rỗng — demo Text-to-SQL không cần nguồn ngoài."""
    with _connect() as conn:
        (count,) = conn.execute("SELECT COUNT(*) FROM luot_ra_vao").fetchone()
        if count:
            return int(count)
        rng = random.Random(42)
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        rows = []
        for _ in range(n_rows):
            day_offset = rng.randint(0, 6)
            hour = rng.randint(6, 20)
            minute = rng.randint(0, 59)
            ts = today - timedelta(days=day_offset)
            ts = ts.replace(hour=hour, minute=minute, second=rng.randint(0, 59))
            rows.append(
                (
                    rng.choice(_AREAS),
                    rng.choice(["vao", "ra"]),
                    rng.choice(_PEOPLE),
                    ts.strftime("%Y-%m-%d %H:%M:%S"),
                )
            )
        conn.executemany(
            "INSERT INTO luot_ra_vao (khu_vuc, huong, nguoi, thoi_gian) VALUES (?, ?, ?, ?)",
            rows,
        )
        return n_rows


# Chỉ SELECT — chặn mọi câu ghi/DDL trước khi chạy (đọc-only theo yêu cầu tài liệu).
_WRITE_KEYWORDS = re.compile(
    r"\b(insert|update|delete|drop|alter|create|attach|pragma|replace|truncate)\b",
    re.IGNORECASE,
)
_MAX_ROWS = 200
_TIMEOUT_S = 3.0


def run_query(sql: str) -> QueryResult:
    """Chạy 1 câu SELECT read-only. Validate trước khi chạy: chỉ SELECT, giới hạn số dòng/thời gian."""
    text = (sql or "").strip().rstrip(";")
    if not text:
        return QueryResult(sql=sql, error="SQL rỗng.")
    if not text.lower().startswith("select"):
        return QueryResult(sql=sql, error="Chỉ cho phép câu SELECT (đọc-only).")
    if _WRITE_KEYWORDS.search(text):
        return QueryResult(sql=sql, error="SQL chứa từ khoá ghi/DDL — bị chặn (đọc-only).")
    if "limit" not in text.lower():
        text = f"{text} LIMIT {_MAX_ROWS}"
    try:
        conn = sqlite3.connect(f"file:{_DB_PATH}?mode=ro", uri=True, timeout=_TIMEOUT_S)
        conn.execute(f"PRAGMA busy_timeout = {int(_TIMEOUT_S * 1000)}")
        start = time.monotonic()
        cur = conn.execute(text)
        columns = [d[0] for d in (cur.description or [])]
        rows = []
        for row in cur:
            if time.monotonic() - start > _TIMEOUT_S:
                break
            rows.append(list(row))
        conn.close()
        return QueryResult(sql=text, columns=columns, rows=rows, row_count=len(rows))
    except sqlite3.Error as exc:
        return QueryResult(sql=text, error=f"Lỗi SQL: {exc}")
