"""Hierarchical Multi-Agent Swarm — một graph cho cả chat và scan.

Bố cục:
  chat/          — team hỏi-đáp: graph.py (CHAT_WORKERS, chat_supervisor LLM, chat_result), nodes.py (guardrail_input, rewrite,
                   scan_team, portfolio_watch, concept_retrieval, memory, answer → save_long_term_memory), state.py; draw_agent/
  scan/          — team quét cảnh báo (kiêm gather cho chat): graph.py wire supervisor + build_* từ <agent>/graph.py,
                   nodes.py (scan_input, HITL), tools.py (scan_tools + tool nộp kết quả), state.py; <agent>/tools.py
  nodes.py       — top_supervisor (tầng 1) + LLM dùng chung
  state.py       — AssistantState (graph gốc); team state ở chat/state.py, scan/state.py
  graph.py       — graph gốc (top_supervisor → chat_team | scan_team), checkpointer, start_graph / resume_graph, vẽ sơ đồ
  steps.py       — helper worker / steps[] cho UI (deps theo request: context của LangGraph, get_runtime().context)
"""

from ai_backend.domain.agents.graph import build_graph, resume_graph, save_graph_visualization, start_graph
from ai_backend.domain.agents.state import AssistantState

__all__ = [
    "AssistantState",
    "build_graph",
    "resume_graph",
    "save_graph_visualization",
    "start_graph",
]
