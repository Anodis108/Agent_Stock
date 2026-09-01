"""ReAct helper — seed → agent ⇄ tools → pack. Dùng chung cho các sub-agent.

Offline (không API key / pytest): giả 1 tool_call (`offline_call`) thay vì
gọi OpenAI thật — test/CI không phụ thuộc network.
"""

from __future__ import annotations

from functools import partial

from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from app.llm import invoke_with_tools, use_offline_tools


def fresh_user(text: str) -> dict:
    from langchain_core.messages import RemoveMessage
    from langgraph.graph.message import REMOVE_ALL_MESSAGES

    return {"messages": [RemoveMessage(id=REMOVE_ALL_MESSAGES), {"role": "user", "content": text}]}


def should_continue(state: dict) -> str:
    last = (state.get("messages") or [None])[-1]
    if getattr(last, "tool_calls", None):
        return "tools"
    return "pack"


def _is_tool_result(msg) -> bool:
    return bool(getattr(msg, "tool_call_id", None) or getattr(msg, "type", None) == "tool")


def agent_node(state: dict, *, tools: list, system_prompt: str, offline_call) -> dict:
    from langchain_core.messages import AIMessage

    last = (state.get("messages") or [None])[-1]
    if use_offline_tools():
        if _is_tool_result(last):
            return {"messages": [AIMessage(content="ok")]}
        name, args = offline_call(state)
        return {
            "messages": [
                AIMessage(
                    content="",
                    tool_calls=[{"name": name, "args": args, "id": "offline-1", "type": "tool_call"}],
                )
            ]
        }

    messages = [{"role": "system", "content": system_prompt}] + list(state.get("messages") or [])
    try:
        response = invoke_with_tools(messages, tools)
    except Exception as exc:
        return {"messages": [AIMessage(content=f"Lỗi LLM: {exc}. Thử lại hoặc hỏi lại câu khác.")]}
    return {"messages": [response]}


def last_tool_json(state: dict, names: set[str]) -> str:
    for m in reversed(list(state.get("messages") or [])):
        name = getattr(m, "name", None) or ""
        if name in names and getattr(m, "content", None):
            return str(m.content)
    return ""


def parse_tool_output(raw: str, cls):
    text = (raw or "").strip()
    if not text:
        return None
    try:
        return cls.model_validate_json(text)
    except Exception:
        return None


def build_react_subgraph(state_cls, *, tools: list, system_prompt: str, offline_call, seed_fn, pack_fn):
    graph = StateGraph(state_cls)
    graph.add_node("seed", seed_fn)
    graph.add_node("agent", partial(agent_node, tools=tools, system_prompt=system_prompt, offline_call=offline_call))
    graph.add_node("tools", ToolNode(tools))
    graph.add_node("pack", pack_fn)
    graph.add_edge(START, "seed")
    graph.add_edge("seed", "agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", "pack": "pack"})
    graph.add_edge("tools", "agent")
    graph.add_edge("pack", END)
    return graph
