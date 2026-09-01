"""Graph DBAgent — ReAct đọc sqlite / soạn pending. COMMIT ở hub HITL.

    START → seed → agent ⇄ tools → pack → END

Đọc: `read_symbol_store`. Có ứng viên crawl: `stage_new_rows` (chưa ghi bảng
chính). Pack ghi `db` + `db_lookup_turn` / `db_write_turn` theo `mode`.
"""

from __future__ import annotations

import json
from functools import lru_cache, partial

from app.agent_pr.db_agent.nodes import approve_pending_write, parse
from app.agent_pr.db_agent.schemas import Agent_Input, Agent_Output
from app.agent_pr.db_agent.state import DBState
from app.agent_pr.db_agent.tools import TOOLS
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from app.agent_pr.react import agent_node, last_tool_json, parse_tool_output, should_continue
from app.monitoring.tracing import current_span, trace_step

__all__ = ["approve_pending_write", "run_db"]

_SYSTEM = """Bạn là DBAgent — đọc sqlite hoặc soạn lệnh ghi. Không crawl, không COMMIT.

Quy tắc:
- Chỉ đọc (không có tin/giá ứng viên) → read_symbol_store đúng một lần.
- Có news_json/prices_json ứng viên → stage_new_rows đúng một lần. Chưa COMMIT — hub HITL mới ghi bảng chính.
- Không tự COMMIT. Không bịa hàng. Không gọi cả hai tool nếu seed đã chỉ một việc.
- describe_db_hitl chỉ khi hỏi vì sao cần duyệt; không thay đọc/soạn.
- Xong tool thì dừng."""


def _seed(state: DBState) -> dict:
    if state.get("messages"):
        return {}
    symbol = str(state.get("symbol") or "").strip() or "?"
    news = state.get("candidate_news") or []
    prices = state.get("candidate_prices") or []
    if news or prices:
        nj = json.dumps(
            [x.model_dump() if hasattr(x, "model_dump") else dict(x) for x in news],
            ensure_ascii=False,
        )
        pj = json.dumps(
            [x.model_dump() if hasattr(x, "model_dump") else dict(x) for x in prices],
            ensure_ascii=False,
        )
        text = (
            f"Soạn lệnh ghi mã {symbol}. news_json={nj} prices_json={pj}. "
            "Gọi stage_new_rows."
        )
    else:
        text = f"Đọc lịch sử DB mã {symbol}. Gọi read_symbol_store."
    return {"messages": [{"role": "user", "content": text}]}


def _query(state: DBState) -> str:
    return str(state.get("symbol") or "")


def _pack(state: DBState) -> dict:
    raw = last_tool_json(state, {"read_symbol_store", "stage_new_rows"})
    result = parse_tool_output(raw, Agent_Output) or parse(state)["result"]
    turn = state.get("turn") or ""
    key = "db_write_turn" if str(state.get("mode") or "read") == "write" else "db_lookup_turn"
    return {"db": result, key: turn}


def _offline(state: DBState) -> tuple[str, dict]:
    symbol = str(state.get("symbol") or "")
    news = state.get("candidate_news") or []
    prices = state.get("candidate_prices") or []
    if news or prices:
        nj = json.dumps(
            [x.model_dump() if hasattr(x, "model_dump") else dict(x) for x in news],
            ensure_ascii=False,
        )
        pj = json.dumps(
            [x.model_dump() if hasattr(x, "model_dump") else dict(x) for x in prices],
            ensure_ascii=False,
        )
        return "stage_new_rows", {"symbol": symbol, "news_json": nj, "prices_json": pj}
    return "read_symbol_store", {"symbol": symbol}


@lru_cache(maxsize=1)
def _build_graph():
    graph = StateGraph(DBState)
    graph.add_node("seed", _seed)
    graph.add_node(
        "agent",
        partial(
            agent_node,
            catalog=TOOLS,
            system_prompt=_SYSTEM,
            query_fn=_query,
            offline_call=_offline,
        ),
    )
    graph.add_node("tools", ToolNode(TOOLS))
    graph.add_node("pack", _pack)
    graph.add_edge(START, "seed")
    graph.add_edge("seed", "agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", "pack": "pack"})
    graph.add_edge("tools", "agent")
    graph.add_edge("pack", END)
    return graph.compile()


def run_db(inp: Agent_Input) -> Agent_Output:
    symbol = (inp.symbol or "").strip().upper()
    with trace_step(None, "agent_pr_db", input=symbol) as t:
        result = _build_graph().invoke(
            {
                "symbol": symbol,
                "candidate_news": inp.candidate_news,
                "candidate_prices": inp.candidate_prices,
                "_trace_span": current_span(),
            }
        )["db"]
        t["output"] = result.detail
        return result
