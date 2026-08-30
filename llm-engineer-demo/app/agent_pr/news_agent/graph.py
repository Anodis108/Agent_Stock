"""Graph news_agent — LangGraph chỉ ráp control flow.

Luồng (tuyến tính, giống craw_agent — chưa conditional / Send):
    START → normalize → fetch → parse → END

So với craw_agent: cùng 3 node, fetch gọi CafeF News.ashx (không vnstock).
Entry `run_news` nhận Agent_Input, trả Agent_Output — không trả cả state.
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.agent_pr.news_agent.nodes import fetch, normalize, parse
from app.agent_pr.news_agent.schemas import Agent_Input, Agent_Output
from app.agent_pr.news_agent.state import NewsState


def _graph():
    """Compile graph. Slice này gọi ít — không cache; fetch luôn gọi CafeF."""
    g = StateGraph(NewsState)
    g.add_node("normalize", normalize)
    g.add_node("fetch", fetch)
    g.add_node("parse", parse)
    g.add_edge(START, "normalize")
    g.add_edge("normalize", "fetch")
    g.add_edge("fetch", "parse")
    g.add_edge("parse", END)
    return g.compile()


async def run_news(inp: Agent_Input) -> Agent_Output:
    """Chạy graph, trả Agent_Output. ainvoke vì route FastAPI là async.

    Lấy `["news"]` sau ainvoke — parse luôn ghi field này; thiếu = bug graph.
    """
    return (await _graph().ainvoke({"symbol": inp.symbol}))["news"]
