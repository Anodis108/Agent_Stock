"""Subgraph db_agent — act ⇄ tools → summarize (runtime source of truth)."""

from __future__ import annotations

from functools import lru_cache

from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from ai_backend.domain.agents.multi_agent._llm import base_llm
from ai_backend.domain.agents.scan.db_agent.state import DBWorkerState
from ai_backend.domain.agents.scan.db_agent.tools import PORTFOLIO_TOOLS, db_results_from_tool_artifacts

SYSTEM_PROMPT = (
    "Bạn là worker dữ liệu người dùng: đọc danh mục nắm giữ và watchlist. "
    "Chỉ dùng số liệu có trong tool / ghi chú, không bịa. Xong việc thì trả lời 1-2 câu tóm tắt kết quả."
)


@lru_cache(maxsize=1)
def _worker_llm():
    return base_llm().bind_tools(PORTFOLIO_TOOLS)


async def act(state: DBWorkerState) -> dict:
    notes = "\n".join(f"[{d}] {n}" for d, n in (state["notes"] or {}).items()) or "(chưa có)"
    messages = state["message_worker"] or [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Nhiệm vụ: {state['task']}\n\nGhi chú từ worker đã chạy:\n{notes}"},
    ]
    response = await _worker_llm().ainvoke(messages)
    return {"message_worker": [response]}


def route_tools(state: DBWorkerState) -> str:
    last = state["message_worker"][-1]
    return "tools" if getattr(last, "tool_calls", None) else "summarize"


def summarize(state: DBWorkerState) -> dict:
    last = state["message_worker"][-1]
    tool_msgs = [m.content for m in state["message_worker"] if getattr(m, "type", None) == "tool"]
    return {"result": "\n".join(tool_msgs) if tool_msgs else last.content, "db_results": db_results_from_tool_artifacts(state["message_worker"])}


@lru_cache(maxsize=1)
def build_db_agent():
    graph = StateGraph(DBWorkerState)
    graph.add_node("act", act)
    graph.add_node("tools", ToolNode(PORTFOLIO_TOOLS, messages_key="message_worker"))
    graph.add_node("summarize", summarize)
    graph.add_edge(START, "act")
    graph.add_conditional_edges("act", route_tools, {"tools": "tools", "summarize": "summarize"})
    graph.add_edge("tools", "act")
    graph.add_edge("summarize", END)
    return graph.compile()
