"""Tầng 1 — top_supervisor (graph gốc) + LLM dùng chung cho mọi agent.

Worker của team chat / scan là subgraph make_agent_graph (multi_agent/hierarchical.py) — xem chat/graph.py, scan/graph.py.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from langchain_core.runnables import RunnableConfig

from common.settings import settings


@lru_cache(maxsize=1)
def _base_llm():
    """LLM chưa bind tool — dùng chung 1 client (ToolNode cần interface LangChain nên dùng ChatOpenAI).

    Ollama / vLLM là OpenAI-compatible → cùng ChatOpenAI, đổi base_url + dummy key theo LLM_BACKEND.
    """
    from langchain_openai import ChatOpenAI

    from ai_backend.infra.llm.backends import get_backend

    backend = get_backend(settings.llm_backend)
    api_key = (settings.api_keys[0] if settings.api_keys else None) if backend.requires_real_key else backend.dummy_key
    return ChatOpenAI(
        model=settings.llm_model,
        temperature=settings.llm_temperature,
        api_key=api_key,
        base_url=settings.llm_base_url or backend.default_base_url or None,
    )


def top_supervisor_node(state: dict[str, Any], config: RunnableConfig) -> dict[str, Any]:
    """Giao yêu cầu cho team phù hợp: câu hỏi người dùng → chat team, quét cảnh báo → scan team."""
    return {"mode": state["mode"] or "chat"}


def route_from_top(state: dict[str, Any]) -> str:
    return "scan_team" if state["mode"] == "scan" else "chat_team"

