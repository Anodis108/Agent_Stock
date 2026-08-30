"""Graph synthesis — một node, không mạng.

    START → compose → END
"""

from __future__ import annotations

from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from app.agent_pr.synthesis_agent.nodes import compose
from app.agent_pr.synthesis_agent.schemas import Agent_Input, Agent_Output
from app.agent_pr.synthesis_agent.state import SynthState
from app.monitoring.tracing import trace_answer


@lru_cache(maxsize=1)
def _build_graph():
    graph = StateGraph(SynthState)
    graph.add_node("compose", compose)
    graph.add_edge(START, "compose")
    graph.add_edge("compose", END)
    return graph.compile()


async def run_synthesis(inp: Agent_Input) -> Agent_Output:
    """Nhận 3 báo cáo (+ n_history), trả answer."""
    with trace_answer("agent_pr_synth", inp.price.symbol) as t:
        result = (
            await _build_graph().ainvoke(
                {
                    "price": inp.price,
                    "news": inp.news,
                    "eval": inp.eval,
                    "n_history": inp.n_history,
                    "_trace_span": t.get("_span"),
                }
            )
        )["result"]
        t["output"] = result.answer
        return result
