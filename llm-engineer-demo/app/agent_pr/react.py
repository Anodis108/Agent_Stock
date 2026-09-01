"""Helper ReAct dùng chung 5 worker — cùng ý agent_m2 (bind_tools + ToolNode).

Mỗi worker tự ráp `_build_graph` (seed → agent ⇄ tools → pack) — Planning Loop.
LLM Brain: `agent_node`. Tools: catalog. Memory: `messages` + sliding window.

Khác agent_m2:
  - HITL không ở worker. Ghi DB dừng ở hub `interrupt_before=["hitl_commit"]`.
  - Offline (không API key / pytest): giả 1 tool_call rồi pack — test/sqlite
    không phụ thuộc OpenAI.
"""

from __future__ import annotations

import os

from app.agent_pr._llm import invoke_with_tools
from app.agent_pr.tool_selection import select_tools
from app.config import settings
from app.guardrails.injection import bound_system


def use_offline_tools() -> bool:
    """Không key, hoặc đang pytest: giả 1 tool_call — không gọi OpenAI."""
    return (not settings.api_keys) or bool(os.environ.get("PYTEST_CURRENT_TEST"))


def should_continue(state: dict) -> str:
    """Còn tool_calls → tools; không → pack (đóng hợp đồng hub)."""
    last = (state.get("messages") or [None])[-1]
    if getattr(last, "tool_calls", None):
        return "tools"
    return "pack"


def _is_tool_result(msg) -> bool:
    return bool(getattr(msg, "tool_call_id", None) or getattr(msg, "type", None) == "tool")


def agent_node(
    state: dict,
    *,
    catalog: list,
    system_prompt: str,
    query_fn,
    offline_call,
) -> dict:
    """Node LLM: retrieve trong catalog → bind → invoke.

    Offline: lần đầu giả đúng 1 tool_call (`offline_call`); lần sau (đã có
    ToolMessage) trả AIMessage rỗng để `should_continue` → pack.
    """
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
    from app.agent_pr.context import sliding_window
    from langchain_core.messages import AIMessage

    query = query_fn(state)
    relevant = select_tools(query, catalog)
    # Cắt short-term worker — nguyên tắc 40–60% / agent_max_messages, tránh context rot.
    history = sliding_window(list(state.get("messages") or []), settings.agent_max_messages)
    messages = [{"role": "system", "content": bound_system(system_prompt)}] + history
    try:
        response = invoke_with_tools(messages, relevant or catalog)
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
