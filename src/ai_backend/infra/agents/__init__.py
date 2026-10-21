"""Hierarchical Multi-Agent Swarm — một graph cho cả chat và scan.

Bố cục:
  chat/          — nhánh hỏi-đáp: team.py (guardrail_input, rewrite, concept, answer, guardrail_output, run_chat_graph)
                   + agent: supervisor_agent, answer_composer, draw_agent (chart_agent, diagram_agent), portfolio_watch_agent
  scan/          — nhánh quét cảnh báo (kiêm lấy dữ liệu cho chat): team.py (event_classifier, hitl gates, synthesis, run_scan_graph)
                   + agent: price_agent, news_agent, eval_agent, event_classifier, synthesis_agent
  nodes.py       — tầng 1–2 supervisor (top / chat / scan) + hàm định tuyến
  state.py       — SwarmState
  graph.py       — build + compile, run_swarm_graph, vẽ sơ đồ (python -m ai_backend.infra.agents.graph)
  events.py / steps.py — deps theo request, event realtime, cờ huỷ, helper worker / steps[] cho UI
"""

from ai_backend.infra.agents.graph import (
    build_swarm_graph,
    compile_swarm_graph,
    list_graph_edges,
    list_graph_nodes,
    run_swarm_graph,
    save_graph_visualization,
)
from ai_backend.infra.agents.chat.team import run_chat_graph
from ai_backend.infra.agents.scan.team import run_scan_graph
from ai_backend.infra.agents.state import SwarmState

__all__ = [
    "SwarmState",
    "build_swarm_graph",
    "compile_swarm_graph",
    "list_graph_edges",
    "list_graph_nodes",
    "run_chat_graph",
    "run_scan_graph",
    "run_swarm_graph",
    "save_graph_visualization",
]
