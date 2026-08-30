"""Graph eval_agent — một node, không IO.

    START → score → END

craw/news tách fetch/parse vì có mạng. Eval chỉ chấm nên gộp một hàm.
"""

from __future__ import annotations

from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from app.agent_pr.eval_agent.nodes import score
from app.agent_pr.eval_agent.schemas import Agent_Input, Agent_Output
from app.agent_pr.eval_agent.state import EvalState
from app.monitoring.tracing import trace_answer


@lru_cache(maxsize=1)
def _build_graph():
    graph = StateGraph(EvalState)
    graph.add_node("score", score)
    graph.add_edge(START, "score")
    graph.add_edge("score", END)
    return graph.compile()


async def run_eval(inp: Agent_Input) -> Agent_Output:
    """Nhận price+news, trả report. Lấy `["report"]` — score luôn ghi field này."""
    with trace_answer("agent_pr_eval", inp.price.symbol) as t:
        report = (
            await _build_graph().ainvoke(
                {"price": inp.price, "news": inp.news, "_trace_span": t.get("_span")}
            )
        )["report"]
        t["output"] = report.detail
        return report
