"""Graph supervisor — hub nối worker (Sơ đồ 3d rút gọn).

    START → normalize → gather → evaluate → assemble → END

gather: craw + news song song. evaluate: eval_agent. assemble: synthesis.
Chưa db/HITL trong graph này.
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.agent_pr.supervisor_agent.nodes import assemble, evaluate, gather, normalize
from app.agent_pr.supervisor_agent.schemas import Agent_Input, Agent_Output
from app.agent_pr.supervisor_agent.state import SupervisorState


def _graph():
    g = StateGraph(SupervisorState)
    g.add_node("normalize", normalize)
    g.add_node("gather", gather)
    g.add_node("evaluate", evaluate)
    g.add_node("assemble", assemble)
    g.add_edge(START, "normalize")
    g.add_edge("normalize", "gather")
    g.add_edge("gather", "evaluate")
    g.add_edge("evaluate", "assemble")
    g.add_edge("assemble", END)
    return g.compile()


async def run_supervisor(inp: Agent_Input) -> Agent_Output:
    """Entry hub. Lấy `["result"]` — assemble luôn ghi field này."""
    return (await _graph().ainvoke({"symbol": inp.symbol}))["result"]
