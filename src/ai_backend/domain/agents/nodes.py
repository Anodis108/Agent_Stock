"""Tầng 1 — top_supervisor (graph gốc). LLM: `infra.llm.client.base_llm` / `completion.*`.

Worker chat/scan: subgraph trong multi_agent/hierarchical.py — xem chat/graph.py, scan/graph.py.
"""

from __future__ import annotations

from typing import Any

from langchain_core.runnables import RunnableConfig


def top_supervisor_node(state: dict[str, Any], config: RunnableConfig) -> dict[str, Any]:
    """Giao yêu cầu cho team phù hợp: câu hỏi người dùng → chat team, quét cảnh báo → scan team."""
    return {"mode": state["mode"] or "chat"}


def route_from_top(state: dict[str, Any]) -> str:
    return "scan_team" if state["mode"] == "scan" else "chat_team"

