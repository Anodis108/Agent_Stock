"""Subgraph price_agent — act ⇄ tools → summarize (runtime source of truth)."""

from __future__ import annotations

from functools import lru_cache

from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from ai_backend.domain.agents.multi_agent._llm import base_llm
from ai_backend.domain.agents.scan.price_agent.state import PriceWorkerState
from ai_backend.domain.agents.scan.price_agent.tools import TOOLS, prices_from_tool_artifacts

SYSTEM_PROMPT = (
    "Bạn là worker giá cổ phiếu: lấy giá lần lượt từng mã trong danh sách, xong mã này mới sang mã kia, "
    "gọi đủ hết rồi mới kết thúc. Chỉ dùng số liệu có trong tool / ghi chú, không bịa. "
    "Xong việc thì trả lời 1-2 câu tóm tắt kết quả."
)


@lru_cache(maxsize=1)
def _worker_llm():
    return base_llm().bind_tools(TOOLS)


async def act(state: PriceWorkerState) -> dict:
    notes = "\n".join(f"[{d}] {n}" for d, n in (state["notes"] or {}).items()) or "(chưa có)"
    syms = ", ".join(state["symbols"]) if "symbols" in state and state["symbols"] else ""
    sym_line = f"\nCác mã (làm lần lượt): {syms}" if syms else ""
    messages = state["message_worker"] or [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Nhiệm vụ: {state['task']}{sym_line}\n\nGhi chú từ worker đã chạy:\n{notes}"},
    ]
    response = await _worker_llm().ainvoke(messages)
    return {"message_worker": [response]}


def route_tools(state: PriceWorkerState) -> str:
    last = state["message_worker"][-1]
    return "tools" if getattr(last, "tool_calls", None) else "summarize"


def summarize(state: PriceWorkerState) -> dict:
    last = state["message_worker"][-1]
    tool_msgs = [m.content for m in state["message_worker"] if getattr(m, "type", None) == "tool"]
    return {"result": "\n".join(tool_msgs) if tool_msgs else last.content, "prices": prices_from_tool_artifacts(state["message_worker"])}


@lru_cache(maxsize=1)
def build_price_agent():
    graph = StateGraph(PriceWorkerState)
    graph.add_node("act", act)
    graph.add_node("tools", ToolNode(TOOLS, messages_key="message_worker"))
    graph.add_node("summarize", summarize)
    
    graph.add_edge(START, "act")
    graph.add_conditional_edges("act", route_tools, {"tools": "tools", "summarize": "summarize"})
    graph.add_edge("tools", "act")
    graph.add_edge("summarize", END)
    return graph.compile()
