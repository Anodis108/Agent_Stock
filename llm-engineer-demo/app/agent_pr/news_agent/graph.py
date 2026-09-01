"""Graph NewsAgent — ReAct lấy tin CafeF thô. Không chấm tốt/xấu (đó là Eval).

    START → seed → agent ⇄ tools → pack → END

Pack ghi `news` (đã trùng tên hub). HITL không ở đây.
"""

from __future__ import annotations

from functools import lru_cache, partial

from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from app.agent_pr.news_agent.schemas import Agent_Input, Agent_Output
from app.agent_pr.news_agent.state import NewsState
from app.agent_pr.news_agent.tools import TOOLS
from app.agent_pr.react import agent_node, last_tool_json, parse_tool_output, should_continue
from app.monitoring.tracing import current_span, trace_step

_SYSTEM = """Bạn là NewsAgent — CHỈ lấy tin thô CafeF. Không chấm tốt/xấu (Eval), không lấy giá, không ghi DB.

Quy tắc:
- Bắt buộc gọi fetch_cafef_news đúng một lần với mã đã chuẩn hoá.
- Không bịa tiêu đề / URL. Không tin thì articles rỗng — không bịa bài.
- describe_news_source chỉ khi hỏi nguồn; không thay fetch.
- Xong tool thì dừng."""


def _seed(state: NewsState) -> dict:
    if state.get("messages"):
        return {}
    symbol = str(state.get("symbol") or "").strip() or "?"
    return {"messages": [{"role": "user", "content": f"Lấy tin CafeF mã {symbol}."}]}


def _query(state: NewsState) -> str:
    return str(state.get("symbol") or "")


def _pack(state: NewsState) -> dict:
    raw = last_tool_json(state, {"fetch_cafef_news"})
    news = parse_tool_output(raw, Agent_Output) or Agent_Output(
        symbol=str(state.get("symbol") or ""),
        articles=[],
        source=raw or str(state.get("error") or "cafef"),
    )
    return {"news": news}


@lru_cache(maxsize=1)
def _build_graph():
    def offline(state: NewsState):
        return "fetch_cafef_news", {"symbol": str(state.get("symbol") or "")}

    graph = StateGraph(NewsState)
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


def run_news(inp: Agent_Input) -> Agent_Output:
    symbol = (inp.symbol or "").strip().upper()
    with trace_step(None, "agent_pr_news", input=symbol) as t:
        news = _build_graph().invoke(
            {"symbol": symbol, "_trace_span": current_span()}
        )["news"]
        t["output"] = {"n_articles": len(news.articles)}
        return news
