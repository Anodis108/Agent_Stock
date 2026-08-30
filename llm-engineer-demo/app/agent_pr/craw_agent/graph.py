"""Graph craw_agent — LangGraph chỉ ráp control flow.

Luồng (tuyến tính, không conditional / Send):
    START → normalize → fetch → parse → END

So với app/agent/graph.py (CRAG): không decompose, không fan-out, không
guardrail LLM. Entry `run_crawl` nhận Agent_Input, trả Agent_Output — không
trả cả state. Debug node thì đọc CrawlState trong test.
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.agent_pr.craw_agent.nodes import fetch, normalize, parse
from app.agent_pr.craw_agent.schemas import Agent_Input, Agent_Output
from app.agent_pr.craw_agent.state import CrawlState


def _graph():
    """Compile graph. Slice 1 gọi ít — không cache; fetch luôn gọi vnstock."""
    g = StateGraph(CrawlState)
    g.add_node("normalize", normalize)
    g.add_node("fetch", fetch)
    g.add_node("parse", parse)
    g.add_edge(START, "normalize")
    g.add_edge("normalize", "fetch")
    g.add_edge("fetch", "parse")
    g.add_edge("parse", END)
    return g.compile()


async def run_crawl(inp: Agent_Input) -> Agent_Output:
    """Chạy graph, trả Agent_Output. ainvoke vì route FastAPI là async.

    Lấy `["quote"]` sau ainvoke — parse luôn ghi field này; thiếu = bug graph,
    để KeyError nổi chứ không trả None.
    """
    return (await _graph().ainvoke({"symbol": inp.symbol}))["quote"]
