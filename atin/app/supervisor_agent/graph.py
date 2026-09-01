"""Graph hub — Phase 1: 1 worker (StatAgent), không HITL/memory.

    START → guardrail_input → stat_agent → reply → guardrail_output → END

Phase 2+ (tối ưu, materialized views, phân quyền phòng ban) sẽ mở rộng thêm
worker/HITL/memory theo lộ trình trong "Ý tưởng Agent.docx" — chưa cần ở Phase 1.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from langgraph.graph import END, START, StateGraph

from app.guardrails.checks import GuardrailViolation
from app.supervisor_agent.guardrails import OUT_OF_SCOPE_REPLY, guardrail_input, guardrail_output
from app.supervisor_agent.nodes import reply, stat_agent
from app.supervisor_agent.schemas import Agent_Input, Agent_Output
from app.supervisor_agent.state import SupervisorState

__all__ = ["Agent_Input", "Agent_Output", "run_supervisor"]


def _route_after_guardrail(state: SupervisorState) -> str:
    return "guardrail_output" if state.get("out_of_scope") else "stat_agent"


@lru_cache(maxsize=1)
def _build_graph():
    graph = StateGraph(SupervisorState)
    graph.add_node("guardrail_input", guardrail_input)
    graph.add_node("stat_agent", stat_agent)
    graph.add_node("reply", reply)
    graph.add_node("guardrail_output", guardrail_output)

    graph.add_edge(START, "guardrail_input")
    graph.add_conditional_edges(
        "guardrail_input",
        _route_after_guardrail,
        {"stat_agent": "stat_agent", "guardrail_output": "guardrail_output"},
    )
    graph.add_edge("stat_agent", "reply")
    graph.add_edge("reply", "guardrail_output")
    graph.add_edge("guardrail_output", END)
    return graph.compile()


def run_supervisor(inp: Agent_Input) -> Agent_Output:
    question = (inp.question or "").strip()
    try:
        out = _build_graph().invoke({"question": question})
    except GuardrailViolation:
        raise
    result = out.get("output") or Agent_Output(question=question, answer=OUT_OF_SCOPE_REPLY)
    result.thread_id = inp.thread_id
    return result


def save_graph_visualization(path: str = "images/agent_stat_graph.png") -> str:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    g = _build_graph().get_graph(xray=True)
    try:
        Path(path).write_bytes(g.draw_mermaid_png())
        return path
    except Exception:
        mmd = path.rsplit(".", 1)[0] + ".mmd"
        Path(mmd).write_text(g.draw_mermaid(), encoding="utf-8")
        return mmd


if __name__ == "__main__":
    print(save_graph_visualization())
