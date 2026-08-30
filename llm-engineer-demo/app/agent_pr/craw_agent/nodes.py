"""Nodes craw_agent — 3 hàm thuần: nhận CrawlState, trả partial dict.

LangGraph chỉ lo thứ tự. Việc thật nằm đây (giống app/agent/nodes.py):
normalize mã, gọi vnstock, đổi nghìn đồng → VND. Không LLM, không LangChain.

`Quote` khởi tạo trong `fetch` — không import vnstock ở đầu file (tránh
banner vnai khi load graph / khi test mã sai chưa tới fetch).
"""

from __future__ import annotations

from app.agent_pr.craw_agent.schemas import Agent_Output
from app.agent_pr.craw_agent.state import CrawlState

ALLOWED = frozenset({"VNM", "HPG", "FPT", "VCB"})


# ── Chuẩn hoá mã ──────────────────────────────────────────────────────────────
#
# Cổng vào graph: "hpg" / " HPG " → "HPG". Mã ngoài ALLOWED raise ngay — không
# tốn lời gọi vnstock (cùng ý với guardrail_input ở app/agent: fail sớm).


def normalize(state: CrawlState) -> dict:
    """Upper + strip; raise ValueError nếu mã chưa nằm whitelist."""
    symbol = str(state.get("symbol") or "").strip().upper()
    if symbol not in ALLOWED:
        raise ValueError(f"Mã '{symbol}' chưa hỗ trợ")
    return {"symbol": symbol}


# ── Lấy rows ──────────────────────────────────────────────────────────────────
#
# Quote.history(KBS): 5 phiên ngày, lấy tail(2) vì parse cần last + prev.
# `close` vẫn nghìn đồng (22.1) — nhân 1000 ở parse, giữ đúng raw API.
#
# Hết data → ValueError. Lỗi mạng/SSL của vnstock để nổi nguyên, chưa bọc.


def fetch(state: CrawlState) -> dict:
    """Gọi vnstock; ghi `rows`. Quote khởi tạo trong hàm này."""
    from vnstock import Quote

    symbol = state["symbol"]
    df = Quote(symbol=symbol, source="KBS").history(length="5", interval="d")
    if df is None or df.empty:
        raise ValueError(f"Không có dữ liệu {symbol}")
    return {
        "rows": [
            {"time": str(row.time), "close": float(row.close)}
            for row in df.tail(2).itertuples()
        ]
    }


# ── Parse ─────────────────────────────────────────────────────────────────────
#
# rows[-1] = phiên mới nhất. trading_date: 10 ký tự đầu của time, bỏ dấu gạch
# ('2026-08-28 07:00:00' → '20260828') — khớp CafeF/Simplize.


def parse(state: CrawlState) -> dict:
    """rows (nghìn đồng) → Agent_Output (VND). Field `quote` là output graph."""
    rows = state["rows"]
    symbol = state["symbol"]
    if not rows:
        raise ValueError("Không có dữ liệu")
    last = float(rows[-1]["close"]) * 1000
    prev = float(rows[-2]["close"]) * 1000 if len(rows) >= 2 else None
    pct = round((last - prev) / prev * 100, 2) if prev else None
    return {
        "quote": Agent_Output(
            symbol=symbol,
            last=last,
            prev_close=prev,
            pct_change=pct,
            trading_date=str(rows[-1].get("time", ""))[:10].replace("-", ""),
        )
    }
