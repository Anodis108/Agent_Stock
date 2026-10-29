"""Graph team chat: dựng subgraph chat (kết quả qua `start_graph` → state checkpoint).

Kiến trúc multi_agent/hierarchical.py (như scan/graph.py): chat_supervisor (LLM, đọc task + notes) chọn worker
scan_team / draw_agent / portfolio_report / concept_retrieval; draw_agent = make_agent_graph(tools, system prompt) — LLM tự quyết.
guardrail_input → (chặn / chào: answer) | rewrite_question → chat_supervisor ⇄ worker → 'done' → answer → save_long_term_memory.
(tạm bỏ guardrail_output — answer stream token kiểu final_answer_node.)
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from ai_backend.domain.agents.chat.draw_agent.graph import build_draw_agent
from ai_backend.domain.agents.chat.nodes import (
    answer_node,
    save_long_term_memory_node,
    concept_retrieval_node,
    guardrail_input_node,
    portfolio_report_node,
    rewrite_node,
    route_after_guardrail,
    scan_team_node,
)
from ai_backend.domain.agents.chat.state import ChatTeamState
from ai_backend.domain.agents.multi_agent._llm import base_llm
from ai_backend.infra.monitoring.tracing import _current, current_span, trace_step

# ── Team chat theo multi_agent/hierarchical.py ───────────────────────────────────────────────────
# chat_supervisor (LLM: task + notes → next_agent) → <worker> → collect → chat_supervisor; 'done' → answer.


async def draw_agent_node(state: dict, config=None) -> dict:
    with trace_step(current_span(), "draw_agent", input={"task": state.get("task")}, as_type="agent") as box:
        token = _current.set(box["_span"]) if box.get("_span") else None
        try:
            out = await build_draw_agent().ainvoke(state, config) if config is not None else await build_draw_agent().ainvoke(state)
            if out.get("result") is not None:
                box["output"] = str(out["result"])[:500]
            return out
        finally:
            if token is not None:
                _current.reset(token)


# Tên worker cho supervisor routing + collect
CHAT_WORKERS = [
    "scan_team",
    "draw_agent",
    "portfolio_report",
    "concept_retrieval",
]

CHAT_SUPERVISOR_SYSTEM = """Bạn điều phối team chat trả lời câu hỏi chứng khoán Việt Nam gồm các worker:
- 'scan_team': thu thập dữ liệu — giá, tin tức, đánh giá kỹ thuật / mức độ biến động của mã, danh mục nắm giữ và watchlist của người dùng
- 'draw_agent': vẽ biểu đồ giá (cần mã) hoặc sơ đồ Mermaid, chỉ khi người dùng yêu cầu vẽ
- 'portfolio_report': lập bảng NAV / lãi lỗ danh mục + watchlist (cần scan_team đọc danh mục người dùng trước)
- 'concept_retrieval': tra tài liệu giải thích khái niệm chứng khoán (câu hỏi "X là gì", không gắn mã cụ thể)
Worker KHÔNG tự giao tiếp với nhau — bạn quyết định worker nào chạy tiếp theo dựa trên nhiệm vụ và ghi chú đã có;
không chạy lại worker đã có kết quả trong ghi chú.

Chọn 'done' khi đã đủ thông tin để trả lời (node answer tổng hợp task + notes, stream token)."""


class _RoutingDecision(BaseModel):
    next_agent: str = Field(description="Tên worker trong system prompt, hoặc 'done'")
    reasoning: str = Field(description="Lý do ngắn gọn cho quyết định")


def _make_collect_node(worker: str):
    """Ghi kết quả worker vào notes + completed_workers; span `<worker>_collect`."""

    def collect(state: dict) -> dict[str, Any]:
        with trace_step(current_span(), f"{worker}_collect", input={"result": (state.get("result") or "")[:300]}, as_type="chain") as box:
            notes = {**state["notes"], worker: state["result"] or ""}
            box["output"] = {"notes_key": worker}
            return {"notes": notes, "completed_workers": [worker]}

    return collect


def _make_route_supervisor(worker_domains: list[str]):
    def route_supervisor(state: ChatTeamState) -> str:
        return state["next_agent"] if state["next_agent"] in worker_domains else "final_answer"

    return route_supervisor


def _make_supervisor_node(name: str, system_prompt: str, worker_domains: list[str]):
    async def supervisor_node(state: dict) -> dict[str, Any]:
        round_n = len(state.get("completed_workers") or []) + 1
        with trace_step(
            current_span(),
            name,
            input={"task": state["task"], "notes": state["notes"]},
            metadata={"round": round_n},
            as_type="generation",
        ) as box:
            notes_text = "\n".join(f"[{d}] {n}" for d, n in state["notes"].items()) or "(chưa có)"
            prompt = f"Nhiệm vụ: {state['task']}\n\nGhi chú từ worker đã chạy:\n{notes_text}"

            decision = await base_llm().with_structured_output(_RoutingDecision).ainvoke(
                [{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}]
            )
            next_agent = decision.next_agent if decision.next_agent in [*worker_domains, "done"] else "done"
            box["output"] = {"next_agent": next_agent, "round": round_n}
        return {"next_agent": next_agent}

    return supervisor_node


@lru_cache(maxsize=1)
def _build_graph():
    """START → guardrail_input → rewrite → chat_supervisor ⇄ worker; 'done' → answer → save_long_term_memory → END."""
    graph = StateGraph(ChatTeamState)
    graph.add_node("guardrail_input", guardrail_input_node)
    graph.add_node("rewrite_question", rewrite_node)
    graph.add_node("chat_supervisor", _make_supervisor_node("chat_supervisor", CHAT_SUPERVISOR_SYSTEM, CHAT_WORKERS))
    graph.add_node("answer", answer_node)
    graph.add_node("save_long_term_memory", save_long_term_memory_node)

    graph.add_node("draw_agent", draw_agent_node)

    graph.add_node("scan_team", scan_team_node)
    graph.add_node("portfolio_report", portfolio_report_node)
    graph.add_node("concept_retrieval", concept_retrieval_node)

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
