"""Graph synthesis — một node, không mạng.

    START → compose → END
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.agent_pr.synthesis_agent.nodes import compose
from app.agent_pr.synthesis_agent.schemas import Agent_Input, Agent_Output
from app.agent_pr.synthesis_agent.state import SynthState


def _graph():
    g = StateGraph(SynthState)
    g.add_node("compose", compose)
    g.add_edge(START, "compose")
    g.add_edge("compose", END)
    return g.compile()


async def run_synthesis(inp: Agent_Input) -> Agent_Output:
    """Nhận 3 báo cáo (+ n_history), trả answer."""
    return (
        await _graph().ainvoke(
            {"price": inp.price, "news": inp.news, "eval": inp.eval, "n_history": inp.n_history}
        )
    )["result"]
