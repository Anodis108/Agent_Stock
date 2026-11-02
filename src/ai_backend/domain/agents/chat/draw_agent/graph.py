"""Subgraph draw_agent — act ⇄ tools → summarize (runtime source of truth)."""

from __future__ import annotations

from functools import lru_cache

from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from ai_backend.domain.agents.chat.draw_agent.state import DrawWorkerState
from ai_backend.domain.agents.chat.draw_agent.tools import TOOLS
from ai_backend.infra.llm.client import bind_tools_llm
from ai_backend.infra.monitoring.tracing import _current, current_span, trace_step
from ai_backend.infra.prompts import get_system_prompt


def _worker_llm():
    return bind_tools_llm(TOOLS)


async def act(state: DrawWorkerState) -> dict:
    with trace_step(current_span(), "act", as_type="generation"):
        notes = "\n".join(f"[{d}] {n}" for d, n in (state["notes"] or {}).items()) or "(chưa có)"
        messages = state["message_worker"] or [
            {"role": "system", "content": get_system_prompt("draw_agent")},
            {"role": "user", "content": f"Nhiệm vụ: {state['task']}\n\nGhi chú từ worker đã chạy:\n{notes}"},
        ]
        response = await _worker_llm().ainvoke(messages)
        return {"message_worker": [response]}


def route_tools(state: DrawWorkerState) -> str:
    last = state["message_worker"][-1]
    return "tools" if getattr(last, "tool_calls", None) else "summarize"


async def tools(state: DrawWorkerState, config=None) -> dict:
    with trace_step(current_span(), "tools", as_type="tool") as box:
        token = _current.set(box["_span"]) if box.get("_span") else None
        try:
            return await ToolNode(TOOLS, messages_key="message_worker").ainvoke(state, config)
        finally:
            if token is not None:
                _current.reset(token)



def summarize(state: DrawWorkerState) -> dict:
    with trace_step(current_span(), "summarize", as_type="chain") as box:
        last = state["message_worker"][-1]
        tool_msgs = [m for m in state["message_worker"] if getattr(m, "type", None) == "tool"]
        drawed = [path for m in tool_msgs for path in m.artifact["drawed"]]
        out = {
            "result": "\n".join(m.content for m in tool_msgs) if tool_msgs else last.content,
            "drawed": drawed,
        }
        box["output"] = str(out["result"])[:500]
        return out


@lru_cache(maxsize=1)
def build_draw_agent():
    graph = StateGraph(DrawWorkerState)
    graph.add_node("act", act)
    graph.add_node("tools", tools)
    graph.add_node("summarize", summarize)
    graph.add_edge(START, "act")
    graph.add_conditional_edges("act", route_tools, {"tools": "tools", "summarize": "summarize"})
    graph.add_edge("tools", "act")
    graph.add_edge("summarize", END)
    return graph.compile()
