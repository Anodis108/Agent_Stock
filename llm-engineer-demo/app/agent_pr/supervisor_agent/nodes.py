"""Nodes hub — chỉ điều phối. Không crawl, không chấm, không ghi DB.

Sơ đồ 3 / 3d: Coordinator parse mã → giao đợt 1 (Price + News + DB song song)
→ thu 3 báo cáo → Eval → Synthesis → trả user. Worker không nói với nhau.

`next_wave` là rule cố định (đủ field nào thì mở đợt đó) — chưa LLM router
(plan.md: QueryCoordinator 2 đợt heuristic). hierarchical.py dùng LLM chọn
worker; ở đây thứ tự đợt đã chốt trên map.
"""

from __future__ import annotations

from langgraph.types import Send

from app.agent_pr.craw_agent import ALLOWED
from app.agent_pr.supervisor_agent.schemas import Agent_Output
from app.agent_pr.supervisor_agent.state import SupervisorState
from app.monitoring.tracing import trace_step


# ── Coordinator: xem đã có báo cáo nào, chọn đợt tiếp ─────────────────────────


def coordinator(state: SupervisorState) -> dict:
    """Hub. Input: symbol + các báo cáo đã về. Output: next_wave + trace.

    Raise ValueError nếu mã ngoài whitelist — fail trước khi Send 3 HTTP.
    """
    symbol = str(state.get("symbol") or "").strip().upper()
    span = state.get("_trace_span")
    with trace_step(span, "coordinator", input=symbol) as t:
        if symbol not in ALLOWED:
            raise ValueError(f"Mã '{symbol}' chưa hỗ trợ")

        trace = list(state.get("trace") or [])
        if not trace:
            trace.append(f"Coordinator parse: ticker={symbol}")

        # Đợt 1 chưa đủ 3 cột — chưa mở Eval (Eval không tự crawl).
        if "price" not in state or "news" not in state or "db" not in state:
            trace.append("Giao đợt 1 → PriceAgent · NewsAgent · DBAgent")
            out = {"symbol": symbol, "next_wave": "wave1", "trace": trace}
        elif "eval" not in state:
            trace.append("Đủ 3 báo cáo đợt 1 → giao EvalAgent")
            out = {"symbol": symbol, "next_wave": "eval", "trace": trace}
        elif "draft" not in state:
            n = len(state["db"].price_history)
            trace.append("Eval xong → giao SynthesisAgent")
            out = {"symbol": symbol, "next_wave": "synth", "n_history": n, "trace": trace}
        else:
            trace.append("Synthesis về hub → trả user")
            out = {"symbol": symbol, "next_wave": "done", "trace": trace}

        t["output"] = {"next_wave": out["next_wave"]}
        return out


def route_coordinator(state: SupervisorState) -> str | list[Send]:
    """Đọc next_wave. Đợt 1 = 3 Send (fan-out). Đợt sau = 1 cạnh về 1 worker.

    Send chỉ đưa field cửa sổ cần — không dump cả SupervisorState xuống worker
    (news/craw cùng `rows` sẽ đè nếu share blackboard).
    """
    wave = state["next_wave"]
    if wave == "wave1":
        # Send CHỈ thấy payload — phải nhét _trace_span (RetrieveTask / GraphState).
        symbol = state["symbol"]
        span = state.get("_trace_span")
        return [
            Send("price_agent", {"symbol": symbol, "_trace_span": span}),
            Send("news_agent", {"symbol": symbol, "_trace_span": span}),
            Send("db_agent", {"symbol": symbol, "_trace_span": span}),
        ]
    if wave == "eval":
        return "eval_agent"
    if wave == "synth":
        return "synth_agent"
    return "reply"


def after_wave1(state: SupervisorState) -> dict:
    """Fan-in đợt 1. Ba worker hội tụ đây — không về thẳng coordinator.

    Nếu 3 nhánh cùng trỏ coordinator, Pregel có thể gọi hub từng nhánh một
    rồi Send đợt 1 lần nữa. Join một node thì hub chỉ chạy khi đủ 3 field.
    """
    price, news, db = state["price"], state["news"], state["db"]
    line = (
        f"đợt 1 về hub: giá {price.source} + {len(news.articles)} tin "
        f"{news.source} + DB {len(db.price_history)} phiên"
    )
    with trace_step(state.get("_trace_span"), "after_wave1", input=state["symbol"]) as t:
        t["output"] = line
        return {"trace": list(state.get("trace") or []) + [line]}


def reply(state: SupervisorState) -> dict:
    """Đóng gói cho user. Synthesis không tự nói UI — hub mới trả `output`."""
    price, news, ev = state["price"], state["news"], state["eval"]
    output = Agent_Output(
        symbol=price.symbol,
        answer=state["draft"].answer,
        price=price,
        news=news,
        eval=ev,
        db=state["db"],
        trace=list(state.get("trace") or []),
    )
    with trace_step(state.get("_trace_span"), "reply", input=price.symbol) as t:
        t["output"] = output.answer
        return {"output": output}
