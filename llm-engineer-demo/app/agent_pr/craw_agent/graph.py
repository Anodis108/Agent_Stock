"""Graph PriceAgent — ReAct lấy giá (vnstock). HITL không ở đây.

    START → seed → agent ⇄ tools → pack → END

IO thật vẫn `nodes.normalize/fetch/parse`; tool chỉ bọc để LLM chọn.
`pack` ghi `price` (tên field hub) — subgraph nhúng thẳng, không lift `quote`.
`run_crawl` dùng cho GET /pr/price; hub gọi `_build_graph()` qua `price_agent`.
"""

from __future__ import annotations

from functools import lru_cache, partial

from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from app.agent_pr.craw_agent.schemas import Agent_Input, Agent_Output
from app.agent_pr.craw_agent.state import CrawlState
from app.agent_pr.craw_agent.tools import TOOLS
from app.agent_pr.react import agent_node, last_tool_json, parse_tool_output, should_continue
from app.monitoring.tracing import current_span, trace_step

_SYSTEM = """Bạn là PriceAgent — CHỈ lấy giá mã niêm yết VN (vnstock KBS). Không lấy tin, không chấm, không ghi DB.

Quy tắc:
- Bắt buộc gọi fetch_latest_close đúng một lần với mã đã chuẩn hoá (HPG, không hpg).
- Không bịa số. last=0 nghĩa là không lấy được — nói vậy, đừng bịa.
- describe_price_source chỉ khi user hỏi nguồn; không thay fetch.
- Xong tool thì dừng, không hỏi lại user."""


def _seed(state: CrawlState) -> dict:
    if state.get("messages"):
        return {}
    symbol = str(state.get("symbol") or "").strip() or "?"
    return {"messages": [{"role": "user", "content": f"Lấy giá đóng cửa mã {symbol}."}]}


def _query(state: CrawlState) -> str:
    return str(state.get("symbol") or "")


def _pack(state: CrawlState) -> dict:
    raw = last_tool_json(state, {"fetch_latest_close"})
    quote = parse_tool_output(raw, Agent_Output) or Agent_Output(
        symbol=str(state.get("symbol") or ""),
        last=0,
        source=raw or str(state.get("error") or "vnstock (không lấy được)"),
    )
    return {"price": quote}


@lru_cache(maxsize=1)
def _build_graph():
    def offline(state: CrawlState):
        return "fetch_latest_close", {"symbol": str(state.get("symbol") or "")}

    graph = StateGraph(CrawlState)
    graph.add_node("seed", _seed)
    graph.add_node(
        "agent",
        partial(
            agent_node,
            catalog=TOOLS,
            system_prompt=_SYSTEM,
            query_fn=_query,
            offline_call=offline,
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


def run_crawl(inp: Agent_Input) -> Agent_Output:
    symbol = (inp.symbol or "").strip().upper()
    with trace_step(None, "agent_pr_price", input=symbol) as t:
        quote = _build_graph().invoke(
            {"symbol": symbol, "_trace_span": current_span()}
        )["price"]
        t["output"] = {"last": quote.last, "pct_change": quote.pct_change}
        return quote
