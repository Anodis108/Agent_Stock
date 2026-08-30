"""Graph eval_agent — một node, không IO.

    START → score → END

craw/news tách fetch/parse vì có mạng. Eval chỉ chấm nên gộp một hàm.
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.agent_pr.eval_agent.nodes import score
from app.agent_pr.eval_agent.schemas import Agent_Input, Agent_Output
from app.agent_pr.eval_agent.state import EvalState


def _graph():
    g = StateGraph(EvalState)
    g.add_node("score", score)
    g.add_edge(START, "score")
    g.add_edge("score", END)
    return g.compile()


async def run_eval(inp: Agent_Input) -> Agent_Output:
    """Nhận price+news, trả report. Lấy `["report"]` — score luôn ghi field này."""
    return (await _graph().ainvoke({"price": inp.price, "news": inp.news}))["report"]
