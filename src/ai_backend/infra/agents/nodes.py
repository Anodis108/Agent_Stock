"""Supervisor của Hierarchical Swarm (tầng 1–2) + hàm định tuyến dùng trong graph.py.

Worker (tầng 3) nằm cùng agent của nó trong agents/ (price_agent, news_agent, eval_agent,
draw_agent, portfolio_watch_agent). Node riêng của từng team nằm ở chat.py / scan.py.
"""

from __future__ import annotations

import time
from typing import Any

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END

from ai_backend.infra.agents.chat.portfolio_watch_agent.nodes import portfolio_watch_intent
from ai_backend.infra.agents.chat.supervisor_agent import route_question
from ai_backend.infra.agents.events import emit_agent_event, graph_deps
from ai_backend.infra.agents.scan.team import has_gate2_proposal, is_abnormal
from ai_backend.infra.agents.state import SwarmState
from ai_backend.infra.monitoring.tracing import agent_span


# ==============================================================================
# Tầng 1–2 — Supervisors (worker: xem agents/)
# ==============================================================================

def top_supervisor_node(state: SwarmState, config: RunnableConfig) -> dict[str, Any]:
    """Giao yêu cầu cho team phù hợp: câu hỏi người dùng → chat team, quét cảnh báo → scan team."""
    return {"mode": state.get("mode") or "chat"}


def route_from_top(state: SwarmState) -> str:
    return "scan_supervisor" if state.get("mode") == "scan" else "guardrail_input"


def chat_supervisor_node(state: SwarmState, config: RunnableConfig) -> dict[str, Any]:
    """Supervisor team chat: lượt đầu lập kế hoạch (LLM/heuristic), các lượt sau xem kết quả worker để giao tiếp."""
    update: dict[str, Any] = {}
    routing = state.get("routing")
    if routing is None:
        cfg = graph_deps.get()
        turn = state.get("turn") or ""
        t0 = time.perf_counter()
        emit_agent_event("node_start", {"node": "supervisor", "timestamp": time.time()})
        rewritten = state["rewritten"]
        with agent_span(turn, "supervisor", input=rewritten.rewritten) as box:
            routing = route_question(rewritten, brain=cfg.get("supervisor_brain"), turn=turn)
            box["output"] = {
                "route": str(getattr(routing.route, "value", routing.route)),
                "agents_to_call": list(routing.agents_to_call or []),
                "reason": routing.reason,
            }
        dur = round(time.perf_counter() - t0, 3)
        emit_agent_event("node_finish", {"node": "supervisor", "duration_s": dur, "duration_ms": int(dur * 1000)})
        update["routing"] = routing

    route = str(getattr(routing.route, "value", routing.route))
    agents = [a.lower() for a in (routing.agents_to_call or [])]
    if route == "retrieval" or "retrieval" in agents:
        update["next"] = ["concept_retrieval"]
        return update
    done = set(state.get("completed") or [])
    need_diagram = route == "diagram" or "diagram" in agents
    has_symbols = bool(state.get("symbols") or state.get("symbol"))
    need_eval = "eval" in agents and bool(state.get("symbol"))
    need_chart = ("chart" in agents or route == "chart") and has_symbols
    need_price = ("price" in agents or need_chart or need_eval) and has_symbols
    need_news = ("news" in agents or need_eval) and has_symbols

    # Bước 1: cần giá / tin → giao scan_supervisor lấy (price_agent, news_agent chỉ nối với scan team)
    gather = [n for n, need in (("price_agent", need_price), ("news_agent", need_news)) if need and n not in done]
    if gather:
        update["gather_request"] = gather
        update["next"] = ["scan_supervisor"]
        return update

    analyze = [
        n
        for n, need in (
            ("eval_agent", need_eval),
            ("draw_agent", need_chart or need_diagram),
            ("portfolio_watch_agent", portfolio_watch_intent(state, agents) is not None),
        )
        if need and n not in done
    ]
    update["next"] = analyze or ["answer"]
    return update





def scan_supervisor_node(state: SwarmState, config: RunnableConfig) -> dict[str, Any]:
    """Supervisor team scan: mỗi lượt xem state hiện tại để giao bước kế tiếp cho tới khi xử lý xong cảnh báo.

    Khi chat_supervisor nhờ lấy dữ liệu (mode="chat"): giao price_agent / news_agent còn thiếu,
    xong thì trả kết quả về chat_supervisor như một agent bình thường.
    """
    if state.get("mode") == "chat":
        done = set(state.get("completed") or [])
        pending = [n for n in (state.get("gather_request") or []) if n not in done]
        return {"next": pending or ["chat_supervisor"]}
    if state.get("error"):
        nxt = [END]
    elif state.get("price") is None or state.get("news") is None:
        nxt = [n for n in ("price_agent", "news_agent") if state.get(n.split("_")[0]) is None]
    elif state.get("event_routing") is None:
        nxt = ["event_classifier"]
    elif not is_abnormal(state["event_routing"].route):
        nxt = [END]
    elif state.get("severity") is None:
        nxt = ["eval_agent"]
    elif has_gate2_proposal(state["severity"]) and not state.get("gate2_pending"):
        nxt = ["hitl_gate_2"]
    elif state.get("alert") is None:
        nxt = ["synthesis_agent"]
    elif not state.get("gate1_action"):
        nxt = ["hitl_gate_1"]
    else:
        nxt = [END]
    return {"next": nxt}


def route_by_next(state: SwarmState) -> list[str]:
    return state.get("next") or [END]


def back_to_team(state: SwarmState) -> str:
    """Worker dùng chung xong việc -> báo lại supervisor của team đang chạy."""
    return "scan_supervisor" if state.get("mode") == "scan" else "chat_supervisor"
