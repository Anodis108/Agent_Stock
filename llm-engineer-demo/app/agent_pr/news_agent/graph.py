"""Graph news_agent — LangGraph chỉ ráp control flow.

Luồng (tuyến tính, giống craw_agent — chưa conditional / Send):
    START → normalize → fetch → parse → END

So với craw_agent: cùng 3 node, fetch gọi CafeF News.ashx (không vnstock).
Entry `run_news` nhận Agent_Input, trả Agent_Output — không trả cả state.
"""

from __future__ import annotations

from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from app.agent_pr.news_agent.nodes import fetch, normalize, parse
from app.agent_pr.news_agent.schemas import Agent_Input, Agent_Output
from app.agent_pr.news_agent.state import NewsState
from app.monitoring.tracing import trace_answer


@lru_cache(maxsize=1)
def _build_graph():
    graph = StateGraph(NewsState)
    graph.add_node("normalize", normalize)
    graph.add_node("fetch", fetch)
    graph.add_node("parse", parse)
    graph.add_edge(START, "normalize")
    graph.add_edge("normalize", "fetch")
    graph.add_edge("fetch", "parse")
    graph.add_edge("parse", END)
    return graph.compile()


async def run_news(inp: Agent_Input) -> Agent_Output:
    """Chạy graph, trả Agent_Output. ainvoke vì route FastAPI là async.

    Lấy `["news"]` sau ainvoke — parse luôn ghi field này; thiếu = bug graph.
    """
    with trace_answer("agent_pr_news", inp.symbol) as t:
        news = (
            await _build_graph().ainvoke(
                {"symbol": inp.symbol, "_trace_span": t.get("_span")}
            )
        )["news"]
        t["output"] = {"n_articles": len(news.articles)}
        return news
