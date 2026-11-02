"""Subgraph eval_agent — act ⇄ tools → summarize (runtime source of truth)."""

from __future__ import annotations

from functools import lru_cache

from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from ai_backend.domain.agents.scan.eval_agent.state import EvalWorkerState
from ai_backend.domain.agents.scan.eval_agent.tools import (
    TOOLS,
    eval_results_from_tool_artifacts,
    proposals_from_tool_artifacts,
)
from ai_backend.infra.llm.client import bind_tools_llm
from ai_backend.infra.monitoring.tracing import _current, current_span, trace_step
from ai_backend.infra.prompts import get_system_prompt


def _worker_llm():
    return bind_tools_llm(TOOLS)


async def act(state: EvalWorkerState) -> dict:
    with trace_step(current_span(), "act", as_type="generation"):
        notes = "\n".join(f"[{d}] {n}" for d, n in (state["notes"] or {}).items()) or "(chưa có)"
        syms = ", ".join(state["symbols"]) if "symbols" in state and state["symbols"] else ""
        sym_line = f"\nCác mã (làm lần lượt): {syms}" if syms else ""
        messages = state["message_worker"] or [
            {"role": "system", "content": get_system_prompt("eval_agent")},
            {"role": "user", "content": f"Nhiệm vụ: {state['task']}{sym_line}\n\nGhi chú từ worker đã chạy:\n{notes}"},
        ]
        response = await _worker_llm().ainvoke(messages)
        return {"message_worker": [response]}


def route_tools(state: EvalWorkerState) -> str:
    last = state["message_worker"][-1]
    return "tools" if getattr(last, "tool_calls", None) else "summarize"


async def tools(state: EvalWorkerState, config=None) -> dict:
    with trace_step(current_span(), "tools", as_type="tool") as box:
        token = _current.set(box["_span"]) if box.get("_span") else None
        try:
            return await ToolNode(TOOLS, messages_key="message_worker").ainvoke(state, config)
        finally:
            if token is not None:
                _current.reset(token)



def summarize(state: EvalWorkerState) -> dict:
    with trace_step(current_span(), "summarize", as_type="chain") as box:
        last = state["message_worker"][-1]
        tool_msgs = [m.content for m in state["message_worker"] if getattr(m, "type", None) == "tool"]
        results = eval_results_from_tool_artifacts(state["message_worker"])
        out = {
            "result": "\n".join(tool_msgs) if tool_msgs else last.content,
            "eval_result": results[-1] if results else None,
            "eval_results": results,
            "messages": proposals_from_tool_artifacts(state["message_worker"]),
        }
        box["output"] = str(out["result"])[:500]
        return out


@lru_cache(maxsize=1)
def build_eval_agent():
    graph = StateGraph(EvalWorkerState)
    graph.add_node("act", act)
    graph.add_node("tools", tools)
    graph.add_node("summarize", summarize)
    graph.add_edge(START, "act")
    graph.add_conditional_edges("act", route_tools, {"tools": "tools", "summarize": "summarize"})
    graph.add_edge("tools", "act")
    graph.add_edge("summarize", END)
    return graph.compile()
