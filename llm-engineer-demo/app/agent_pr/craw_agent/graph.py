"""Graph craw_agent — LangGraph chỉ ráp control flow.

Luồng (tuyến tính, không conditional / Send):
    START → normalize → fetch → parse → END

So với app/agent/graph.py (CRAG): không decompose, không fan-out, không
guardrail LLM. Entry `run_crawl` nhận Agent_Input, trả Agent_Output — không
trả cả state. Debug node thì đọc CrawlState trong test.
"""

from __future__ import annotations

from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from app.agent_pr.craw_agent.nodes import fetch, normalize, parse
from app.agent_pr.craw_agent.schemas import Agent_Input, Agent_Output
from app.agent_pr.craw_agent.state import CrawlState
from app.monitoring.tracing import trace_answer


@lru_cache(maxsize=1)
def _build_graph():
    graph = StateGraph(CrawlState)
    graph.add_node("normalize", normalize)
    graph.add_node("fetch", fetch)
    graph.add_node("parse", parse)
    graph.add_edge(START, "normalize")
    graph.add_edge("normalize", "fetch")
    graph.add_edge("fetch", "parse")
    graph.add_edge("parse", END)
    return graph.compile()


async def run_crawl(inp: Agent_Input) -> Agent_Output:
    """Chạy graph, trả Agent_Output. ainvoke vì route FastAPI là async.

    Lấy `["quote"]` sau ainvoke — parse luôn ghi field này; thiếu = bug graph,
    để KeyError nổi chứ không trả None.
    """
    with trace_answer("agent_pr_price", inp.symbol) as t:
        quote = (
            await _build_graph().ainvoke(
                {"symbol": inp.symbol, "_trace_span": t.get("_span")}
            )
        )["quote"]
        t["output"] = {"last": quote.last, "pct_change": quote.pct_change}
        return quote
