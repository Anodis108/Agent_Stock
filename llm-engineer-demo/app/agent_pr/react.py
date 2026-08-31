"""Vòng ReAct dùng chung worker agent_pr — giống agent_m2 (bind_tools + ToolNode).

Graph: seed → agent ⇄ tools → pack → END.
`catalog` = tool của ĐÚNG agent đó. `pack` đọc ToolMessage → field hợp đồng
(quote / news / report / result). Không HITL ở worker (HITL ghi DB ở hub).

Không API key: giả 1 tool_call (pytest/sqlite) rồi pack — không vòng lặp.
"""

from __future__ import annotations

import os
from functools import lru_cache

from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from app.agent_pr.tool_selection import select_tools
from app.config import settings


def use_offline_tools() -> bool:
    """Không key, hoặc đang pytest: giả 1 tool_call — test/sqlite không phụ thuộc OpenAI."""
    return (not settings.api_keys) or bool(os.environ.get("PYTEST_CURRENT_TEST"))


@lru_cache(maxsize=1)
def base_llm():
    """Client ChatOpenAI tái dùng — bind_tools mỗi lượt (catalog/top-k đổi)."""
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=settings.llm_model,
        temperature=settings.llm_temperature,
        api_key=settings.api_keys[0] if settings.api_keys else None,
    )


def should_continue(state: dict) -> str:
    last = (state.get("messages") or [None])[-1]
    if getattr(last, "tool_calls", None):
        return "tools"
    return "pack"


def _is_tool_result(msg) -> bool:
    return bool(getattr(msg, "tool_call_id", None) or getattr(msg, "type", None) == "tool")


def make_agent_node(catalog: list, system_prompt: str, query_fn, offline_call):
    """Node LLM: retrieve tool trong catalog → bind → ainvoke."""

    async def agent_node(state: dict) -> dict:
        last = (state.get("messages") or [None])[-1]
        if use_offline_tools():
            from langchain_core.messages import AIMessage

            if _is_tool_result(last):
                return {"messages": [AIMessage(content="ok")]}
            name, args = offline_call(state)
            return {
                "messages": [
                    AIMessage(
                        content="",
                        tool_calls=[
                            {
                                "name": name,
                                "args": args,
                                "id": "offline-1",
                                "type": "tool_call",
                            }
                        ],
                    )
                ]
            }
        query = query_fn(state)
        relevant = select_tools(query, catalog)
        llm = base_llm().bind_tools(relevant or catalog)
        messages = [{"role": "system", "content": system_prompt}] + list(
            state.get("messages") or []
        )
        response = await llm.ainvoke(messages)
        return {"messages": [response]}

    return agent_node


def compile_react(
    *,
    state_schema,
    catalog: list,
    system_prompt: str,
    query_fn,
    seed,
    pack,
    offline_call,
):
    """Ráp 4 node. `offline_call(state) -> (tool_name, args)` khi không có API key."""
    graph = StateGraph(state_schema)
    graph.add_node("seed", seed)
    graph.add_node("agent", make_agent_node(catalog, system_prompt, query_fn, offline_call))
    graph.add_node("tools", ToolNode(catalog))
    graph.add_node("pack", pack)
    graph.add_edge(START, "seed")
    graph.add_edge("seed", "agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", "pack": "pack"})
    graph.add_edge("tools", "agent")
    graph.add_edge("pack", END)
    return graph.compile()


def last_tool_json(state: dict, names: set[str]) -> str:
    """Nội dung ToolMessage mới nhất thuộc `names` (JSON tool trả về)."""
    for m in reversed(list(state.get("messages") or [])):
        name = getattr(m, "name", None) or ""
        if name in names and getattr(m, "content", None):
            return str(m.content)
    return ""
