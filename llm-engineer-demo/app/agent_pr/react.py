"""Helper ReAct dùng chung 5 worker — cùng ý agent_m2 (bind_tools + ToolNode).

Mỗi worker tự ráp `_build_graph` (seed → agent ⇄ tools → pack) — Planning Loop.
LLM Brain: `agent_node`. Tools: catalog. Memory: `messages` + sliding window.

Khác agent_m2: HITL không ở worker. Ghi DB dừng ở hub `interrupt_before=["hitl_commit"]`.
"""

from __future__ import annotations

from functools import partial

from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from app.agent_pr._llm import invoke_with_tools
from app.agent_pr.tool_selection import select_tools
from app.config import settings
from app.guardrails.injection import bound_system
from app.monitoring.tracing import step_parent


def fresh_user(text: str) -> dict:
    """Seed đầu subgraph: xóa messages cũ (checkpointer giữ từ lượt HTTP trước)."""
    from langchain_core.messages import RemoveMessage
    from langgraph.graph.message import REMOVE_ALL_MESSAGES

    return {
        "messages": [
            RemoveMessage(id=REMOVE_ALL_MESSAGES),
            {"role": "user", "content": text},
        ]
    }


def should_continue(state: dict) -> str:
    """Còn tool_calls → tools; không → pack (đóng hợp đồng hub)."""
    last = (state.get("messages") or [None])[-1]
    if getattr(last, "tool_calls", None):
        return "tools"
    return "pack"


def agent_node(
    state: dict,
    *,
    catalog: list,
    system_prompt: str,
    query_fn,
    agent_name: str,
) -> dict:
    """Node LLM: retrieve trong catalog → bind → invoke.

    `agent_name` ("price_agent"/"db_agent"/...) chọn đúng span cha (xem
    tracing.step_parent) để "llm.bind_tools" lồng dưới agent, không phải root.
    """
    from app.agent_pr.context import sliding_window
    from langchain_core.messages import AIMessage

    relevant = select_tools(query_fn(state), catalog)
    # Cắt short-term worker — nguyên tắc 40–60% / agent_max_messages, tránh context rot.
    history = sliding_window(list(state.get("messages") or []), settings.agent_max_messages)
    messages = [{"role": "system", "content": bound_system(system_prompt)}] + history
    try:
        response = invoke_with_tools(
            messages, relevant or catalog, step_parent(state, agent_name), turn=str(state.get("turn") or "")
        )
    except Exception as exc:
        return {
            "messages": [
                AIMessage(
                    content=(
                        f"Lỗi LLM: {exc}. Thử lại, hỏi user, hoặc dùng tool khác."
                    )
                )
            ]
        }
    return {"messages": [response]}


def last_tool_json(state: dict, names: set[str]) -> str:
    """JSON từ ToolMessage mới nhất thuộc `names` — pack không parse lại IO."""
    for m in reversed(list(state.get("messages") or [])):
        name = getattr(m, "name", None) or ""
        if name in names and getattr(m, "content", None):
            return str(m.content)
    return ""


def parse_tool_output(raw: str, cls):
    """JSON → model. Sai JSON / text lỗi → None — pack không raise, graph không crash."""
    text = (raw or "").strip()
    if not text:
        return None
    try:
        return cls.model_validate_json(text)
    except Exception:
        return None


def build_react_subgraph(
    state_cls,
    *,
    tools: list,
    system_prompt: str,
    query_fn,
    agent_name: str,
    seed_fn,
    pack_fn,
):
    """Khung seed → agent ⇄ tools → pack — giống hệt nhau ở cả 5 worker
    (craw/news/db/eval/synth), chỉ khác state/tools/prompt/seed/pack. Trả về
    graph CHƯA compile — caller tự `.compile()` (giữ @lru_cache ở call site)."""
    graph = StateGraph(state_cls)
    graph.add_node("seed", seed_fn)
    graph.add_node(
        "agent",
        partial(
            agent_node,
            catalog=tools,
            system_prompt=system_prompt,
            query_fn=query_fn,
            agent_name=agent_name,
        ),
    )
    graph.add_node("tools", ToolNode(tools))
    graph.add_node("pack", pack_fn)
    
    graph.add_edge(START, "seed")
    graph.add_edge("seed", "agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", "pack": "pack"})
    graph.add_edge("tools", "agent")
    graph.add_edge("pack", END)
    return graph
