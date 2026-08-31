"""Nodes craw_agent — 3 hàm thuần: nhận CrawlState, trả partial dict.

LangGraph chỉ lo thứ tự. Việc thật nằm đây (giống app/agent/nodes.py):
normalize mã, gọi vnstock, đổi nghìn đồng → VND. Không LLM, không LangChain.

`Quote` khởi tạo trong `fetch` — không import vnstock ở đầu file (tránh
banner vnai khi load graph / khi test mã sai chưa tới fetch).
"""

from __future__ import annotations

from app.agent_pr.craw_agent.schemas import Agent_Output
from app.agent_pr.craw_agent.state import CrawlState
from app.agent_pr.symbol import normalize_symbol
from app.monitoring.tracing import trace_step


# ── Chuẩn hoá mã ──────────────────────────────────────────────────────────────
#
# Cổng vào graph: "hpg" / " HPG " → "HPG". Sai định dạng raise ngay — không
# tốn lời gọi vnstock (cùng ý với guardrail_input ở app/agent: fail sớm).


def normalize(state: CrawlState) -> dict:
    """Upper + strip; raise ValueError nếu không giống mã niêm yết."""
    with trace_step(state.get("_trace_span"), "craw_normalize", input=state.get("symbol", "")) as t:
        symbol = normalize_symbol(str(state.get("symbol") or ""))
        t["output"] = symbol
        return {"symbol": symbol}


# ── Lấy rows ──────────────────────────────────────────────────────────────────
#
# Quote.history(KBS): 5 phiên ngày, lấy tail(2) vì parse cần last + prev.
# `close` vẫn nghìn đồng (22.1) — nhân 1000 ở parse, giữ đúng raw API.
#
# Hết data → rows rỗng (parse vẫn trả quote). Lỗi mạng Docker/DNS không crash graph.


def fetch(state: CrawlState) -> dict:
    """Gọi vnstock; ghi `rows`. Quote khởi tạo trong hàm này."""
    from vnstock import Quote

    symbol = state["symbol"]
    with trace_step(state.get("_trace_span"), "craw_fetch", input=symbol) as t:
        try:
            df = Quote(symbol=symbol, source="KBS").history(length="5", interval="d")
        except Exception as exc:
            t["output"] = {"error": str(exc)}
            return {"rows": []}
        if df is None or df.empty:
            t["output"] = {"n_rows": 0}
            return {"rows": []}
        rows = [
            {"time": str(row.time), "close": float(row.close)}
            for row in df.tail(2).itertuples()
        ]
        t["output"] = {"n_rows": len(rows)}
        return {"rows": rows}


# ── Parse ─────────────────────────────────────────────────────────────────────
#
# rows[-1] = phiên mới nhất. trading_date: 10 ký tự đầu của time, bỏ dấu gạch
# ('2026-08-28 07:00:00' → '20260828') — khớp CafeF/Simplize.


def parse(state: CrawlState) -> dict:
    """rows (nghìn đồng) → Agent_Output (VND). Field `quote` là output graph."""
    rows = state["rows"]
    symbol = state["symbol"]
    with trace_step(state.get("_trace_span"), "craw_parse", input=symbol) as t:
        if not rows:
            quote = Agent_Output(symbol=symbol, last=0, source="vnstock (không lấy được)")
            t["output"] = {"last": 0, "empty": True}
            return {"quote": quote}
        last = float(rows[-1]["close"]) * 1000
        prev = float(rows[-2]["close"]) * 1000 if len(rows) >= 2 else None
        pct = round((last - prev) / prev * 100, 2) if prev else None
        quote = Agent_Output(
            symbol=symbol,
            last=last,
            prev_close=prev,
            pct_change=pct,
            trading_date=str(rows[-1].get("time", ""))[:10].replace("-", ""),
        )
        t["output"] = {"last": last, "pct_change": pct}
        return {"quote": quote}
