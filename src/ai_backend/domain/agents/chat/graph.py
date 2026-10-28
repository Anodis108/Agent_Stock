"""Graph team chat: dựng subgraph chat (kết quả qua `start_graph` → state checkpoint).

Kiến trúc multi_agent/hierarchical.py (như scan/graph.py): chat_supervisor (LLM, đọc task + notes) chọn worker
scan_team / draw_agent / portfolio_watch / concept_retrieval; draw_agent = make_agent_graph(tools, system prompt) — LLM tự quyết.
guardrail_input → (chặn / chào: answer) | rewrite_question → chat_supervisor ⇄ worker → 'done' → answer → save_long_term_memory.
(tạm bỏ guardrail_output — answer stream token kiểu final_answer_node.)
"""

from __future__ import annotations

from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from ai_backend.domain.agents.chat.draw_agent.state import DrawWorkerState
from ai_backend.domain.agents.chat.draw_agent.tools import TOOLS as DRAW_TOOLS
from ai_backend.domain.agents.chat.nodes import (
    answer_node,
    save_long_term_memory_node,
    concept_retrieval_node,
    guardrail_input_node,
    portfolio_watch_node,
    rewrite_node,
    route_after_guardrail,
    scan_team_node,
)
from ai_backend.domain.agents.chat.state import ChatTeamState
from ai_backend.domain.agents.multi_agent.hierarchical import _make_route_supervisor, make_agent_graph
from ai_backend.domain.agents.scan.graph import _make_collect_node, _make_supervisor_node

# ── Team chat theo multi_agent/hierarchical.py ───────────────────────────────────────────────────
# chat_supervisor (LLM: task + notes → next_agent) → <worker> → collect → chat_supervisor; 'done' → answer.

_RULES = "Chỉ dùng số liệu có trong tool / ghi chú, không bịa. Xong việc thì trả lời 1-2 câu tóm tắt kết quả."

# Agent (subgraph make_agent_graph): tool + system prompt + state riêng (<agent>/state.py kế thừa WorkerState)
CHAT_AGENTS: dict[str, tuple[list, str, type]] = {
    "draw_agent": (
        DRAW_TOOLS,
        "Bạn là worker vẽ: biểu đồ giá cho các mã trong nhiệm vụ bằng draw_price_chart (tự chọn chart_type, số phiên "
        "theo yêu cầu), sơ đồ quy trình / quan hệ bằng draw_diagram. Chỉ vẽ đúng thứ người dùng yêu cầu.",
        DrawWorkerState,
    ),
}
# Node (không vòng LLM / tool)
CHAT_NODES = {
    "scan_team": scan_team_node,
    "portfolio_watch": portfolio_watch_node,
    "concept_retrieval": concept_retrieval_node,
}
CHAT_WORKERS = [*CHAT_AGENTS, *CHAT_NODES]

CHAT_SUPERVISOR_SYSTEM = """Bạn điều phối team chat trả lời câu hỏi chứng khoán Việt Nam gồm các worker:
- 'scan_team': thu thập dữ liệu — giá, tin tức, đánh giá kỹ thuật / mức độ biến động của mã, danh mục nắm giữ và watchlist của người dùng
- 'draw_agent': vẽ biểu đồ giá (cần mã) hoặc sơ đồ Mermaid, chỉ khi người dùng yêu cầu vẽ
- 'portfolio_watch': lập bảng NAV / lãi lỗ danh mục + watchlist (cần scan_team đọc danh mục người dùng trước)
- 'concept_retrieval': tra tài liệu giải thích khái niệm chứng khoán (câu hỏi "X là gì", không gắn mã cụ thể)
Worker KHÔNG tự giao tiếp với nhau — bạn quyết định worker nào chạy tiếp theo dựa trên nhiệm vụ và ghi chú đã có;
không chạy lại worker đã có kết quả trong ghi chú.

Chọn 'done' khi đã đủ thông tin để trả lời (node answer tổng hợp task + notes, stream token)."""

@lru_cache(maxsize=1)
def _build_graph():
    """START → guardrail_input → rewrite → chat_supervisor ⇄ worker; 'done' → answer → save_long_term_memory → END."""
    graph = StateGraph(ChatTeamState)
    graph.add_node("guardrail_input", guardrail_input_node)
    graph.add_node("rewrite_question", rewrite_node)
    graph.add_node("chat_supervisor", _make_supervisor_node("chat_supervisor", CHAT_SUPERVISOR_SYSTEM, CHAT_WORKERS))
    graph.add_node("answer", answer_node)
    graph.add_node("save_long_term_memory", save_long_term_memory_node)

    for agent, (tools, prompt, state) in CHAT_AGENTS.items():
        graph.add_node(agent, make_agent_graph(agent, tools, f"{prompt} {_RULES}", state))
    for name, node in CHAT_NODES.items():
        graph.add_node(name, node)

    routing_map = {"final_answer": "answer"}  # supervisor 'done' → answer (final_answer)
    for worker in CHAT_WORKERS:
        graph.add_node(f"{worker}_collect", _make_collect_node(worker))
        graph.add_edge(worker, f"{worker}_collect")
        graph.add_edge(f"{worker}_collect", "chat_supervisor")
        routing_map[worker] = worker

    graph.add_edge(START, "guardrail_input")
    graph.add_conditional_edges("guardrail_input", route_after_guardrail, ["answer", "rewrite_question"])
    graph.add_edge("rewrite_question", "chat_supervisor")
    graph.add_conditional_edges("chat_supervisor", _make_route_supervisor(CHAT_WORKERS), routing_map)
    graph.add_edge("answer", "save_long_term_memory")
    graph.add_edge("save_long_term_memory", END)
    return graph.compile()



