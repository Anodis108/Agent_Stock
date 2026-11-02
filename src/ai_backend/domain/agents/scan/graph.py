"""Graph team scan: dựng subgraph scan (`start_graph` / `resume_graph` → state checkpoint).

Kiến trúc multi_agent/hierarchical.py: scan_supervisor (LLM, đọc task + notes) chọn worker
price_agent / news_agent / db_agent / event_classifier_node / eval_agent [đề xuất update_watchlist]
/ synthesis_node [soạn + gửi cảnh báo ngay qua notifier]; mỗi ReAct worker = `build_*_agent()` từ folder riêng.

HITL (chỉ update_watchlist của eval_agent) giống llm-engineer-demo: hành động đề xuất = AIMessage.tool_calls trong `messages`; graph DỪNG
trước scan_tools (interrupt_before) → status="pending_approval" + thread_id; resume_graph duyệt/từ chối.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel, Field

from ai_backend.domain.agents.scan.db_agent.graph import build_db_agent
from ai_backend.domain.agents.scan.eval_agent.graph import build_eval_agent
from ai_backend.domain.agents.scan.news_agent.graph import build_news_agent
from ai_backend.domain.agents.scan.nodes import event_classifier_node, synthesis_node
from ai_backend.domain.agents.scan.price_agent.graph import build_price_agent
from ai_backend.domain.agents.scan.state import ScanHierarchicalState
from ai_backend.domain.agents.scan.tools import SCAN_ACTION_TOOLS
from ai_backend.infra.llm.client import base_llm
from ai_backend.infra.monitoring.tracing import _current, current_span, trace_step
from ai_backend.infra.prompts import get_system_prompt
from ai_backend.shared.logging import get_logger


async def scan_tools_node(state: dict, config=None) -> dict:
    with trace_step(current_span(), "scan_tools", as_type="tool") as box:
        token = _current.set(box["_span"]) if box.get("_span") else None
        try:
            return await ToolNode(SCAN_ACTION_TOOLS, messages_key="messages").ainvoke(state, config)
        finally:
            if token is not None:
                _current.reset(token)


async def price_agent_node(state: dict, config=None) -> dict:
    with trace_step(current_span(), "price_agent", input={"task": state.get("task")}, as_type="agent") as box:
        token = _current.set(box["_span"]) if box.get("_span") else None
        try:
            out = await build_price_agent().ainvoke(state, config) if config is not None else await build_price_agent().ainvoke(state)
            if out.get("result") is not None:
                box["output"] = str(out["result"])[:500]
            return out
        finally:
            if token is not None:
                _current.reset(token)


async def news_agent_node(state: dict, config=None) -> dict:
    with trace_step(current_span(), "news_agent", input={"task": state.get("task")}, as_type="agent") as box:
        token = _current.set(box["_span"]) if box.get("_span") else None
        try:
            out = await build_news_agent().ainvoke(state, config) if config is not None else await build_news_agent().ainvoke(state)
            if out.get("result") is not None:
                box["output"] = str(out["result"])[:500]
            return out
        finally:
            if token is not None:
                _current.reset(token)


async def db_agent_node(state: dict, config=None) -> dict:
    with trace_step(current_span(), "db_agent", input={"task": state.get("task")}, as_type="agent") as box:
        token = _current.set(box["_span"]) if box.get("_span") else None
        try:
            out = await build_db_agent().ainvoke(state, config) if config is not None else await build_db_agent().ainvoke(state)
            if out.get("result") is not None:
                box["output"] = str(out["result"])[:500]
            return out
        finally:
            if token is not None:
                _current.reset(token)


async def eval_agent_node(state: dict, config=None) -> dict:
    with trace_step(current_span(), "eval_agent", input={"task": state.get("task")}, as_type="evaluator") as box:
        token = _current.set(box["_span"]) if box.get("_span") else None
        try:
            out = await build_eval_agent().ainvoke(state, config) if config is not None else await build_eval_agent().ainvoke(state)
            if out.get("result") is not None:
                box["output"] = str(out["result"])[:500]
            return out
        finally:
            if token is not None:
                _current.reset(token)


_logger = get_logger(__name__)

# Tên worker cho supervisor routing + collect
SCAN_WORKERS = [
    "price_agent",
    "news_agent",
    "db_agent",
    "event_classifier_node",
    "eval_agent",
    "synthesis_node",
]

class _RoutingDecision(BaseModel):
    next_agent: str = Field(description="Tên worker trong system prompt, hoặc 'done'")
    reasoning: str = Field(description="Lý do ngắn gọn cho quyết định")


def route_collect(state: ScanHierarchicalState) -> str:
    """Sau eval_agent: còn tool_call (update_watchlist) → scan_tools; không thì → scan_supervisor."""
    messages = state["messages"]
    pending = bool(messages) and bool(getattr(messages[-1], "tool_calls", None))
    return "scan_tools" if pending else "scan_supervisor"


def _make_collect_node(worker: str):
    """Ghi notes + completed_workers; span `<worker>_collect` dưới parent hiện tại."""

    def collect(state: dict) -> dict[str, Any]:
        with trace_step(current_span(), f"{worker}_collect", input={"result": (state.get("result") or "")[:300]}, as_type="chain") as box:
            notes = {**state["notes"], worker: state["result"] or ""}
            box["output"] = {"notes_key": worker}
            return {"notes": notes, "completed_workers": [worker]}

    return collect


def _make_route_supervisor(worker_domains: list[str]):
    def route_supervisor(state: ScanHierarchicalState) -> str:
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
def build_graph():
    """START → scan_supervisor → <worker> → <worker>_collect → …; 'done' → END."""
    graph = StateGraph(ScanHierarchicalState)
    graph.add_node(
        "scan_supervisor",
        _make_supervisor_node("scan_supervisor", get_system_prompt("scan_supervisor"), SCAN_WORKERS),
    )
    graph.add_node("scan_tools", scan_tools_node)
    graph.add_node("price_agent", price_agent_node)
    graph.add_node("news_agent", news_agent_node)
    graph.add_node("db_agent", db_agent_node)
    graph.add_node("eval_agent", eval_agent_node)

    graph.add_node("event_classifier_node", event_classifier_node)
    graph.add_node("synthesis_node", synthesis_node)

    # HITL chỉ sau eval_agent (update_watchlist); synthesis chỉ ghi alert, collect → supervisor.
    hitl_workers = {"eval_agent"}
    routing_map = {"final_answer": END}  # supervisor chọn 'done' → kết thúc team
    for worker in SCAN_WORKERS:
        graph.add_node(f"{worker}_collect", _make_collect_node(worker))
        graph.add_edge(worker, f"{worker}_collect")
        if worker in hitl_workers:
            graph.add_conditional_edges(f"{worker}_collect", route_collect, ["scan_supervisor", "scan_tools"])
        else:
            graph.add_edge(f"{worker}_collect", "scan_supervisor")
        routing_map[worker] = worker

    graph.add_edge(START, "scan_supervisor")
    graph.add_conditional_edges("scan_supervisor", _make_route_supervisor(SCAN_WORKERS), routing_map)
    graph.add_edge("scan_tools", "scan_supervisor")
    return graph.compile(interrupt_before=["scan_tools"])
