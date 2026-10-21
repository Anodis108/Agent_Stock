"""Dựng, compile và chạy Hierarchical Multi-Agent Swarm (wiring node/edge, run_swarm_graph, visualize)."""

from __future__ import annotations

import time
from functools import lru_cache
from pathlib import Path
from typing import Any

from langchain_core.runnables import RunnableConfig

from langgraph.graph import END, START, StateGraph

from ai_backend.infra.agents.chat.team import (
    answer_node,
    concept_retrieval_node,
    guardrail_input_node,
    guardrail_output_node,
    rewrite_node,
    route_after_guardrail,
)
from ai_backend.infra.agents.chat.draw_agent import draw_agent_node
from ai_backend.infra.agents.scan.eval_agent.nodes import eval_agent_node
from ai_backend.infra.agents.scan.news_agent.nodes import news_agent_node
from ai_backend.infra.agents.chat.portfolio_watch_agent.nodes import portfolio_watch_node
from ai_backend.infra.agents.scan.price_agent.nodes import price_agent_node
from ai_backend.infra.agents.nodes import (
    back_to_team,
    chat_supervisor_node,
    route_by_next,
    route_from_top,
    scan_supervisor_node,
    top_supervisor_node,
)
from ai_backend.infra.agents.scan.team import (
    event_classifier_node,
    hitl_gate_1_node,
    hitl_gate_2_node,
    synthesis_node,
)
from ai_backend.infra.agents.events import graph_deps
from ai_backend.infra.agents.state import SwarmState
from ai_backend.infra.monitoring.tracing import trace_request

CHAT_WORKERS = ("eval_agent", "draw_agent", "portfolio_watch_agent")
SCAN_STEPS = ("event_classifier", "hitl_gate_2", "synthesis_agent", "hitl_gate_1")


def build_swarm_graph() -> StateGraph:
    """Dựng Hierarchical Swarm Graph.

    top_supervisor → chat_supervisor | scan_supervisor → worker → quay về supervisor đã giao việc.
    price_agent / news_agent chỉ nối với scan_supervisor; chat cần dữ liệu thì nhờ scan_supervisor lấy.
    Mọi câu trả lời cho khách đi qua answer → guardrail_output.
    """
    graph = StateGraph(SwarmState)

    # Tầng 1–2: supervisor
    graph.add_node("top_supervisor", top_supervisor_node)
    graph.add_node("chat_supervisor", chat_supervisor_node)
    graph.add_node("scan_supervisor", scan_supervisor_node)

    # Tầng 3: worker
    graph.add_node("price_agent", price_agent_node)
    graph.add_node("news_agent", news_agent_node)
    graph.add_node("eval_agent", eval_agent_node)
    graph.add_node("draw_agent", draw_agent_node)
    graph.add_node("portfolio_watch_agent", portfolio_watch_node)

    # Node riêng team chat
    graph.add_node("guardrail_input", guardrail_input_node)
    graph.add_node("rewrite_question", rewrite_node)
    graph.add_node("concept_retrieval", concept_retrieval_node)
    graph.add_node("answer", answer_node)
    graph.add_node("guardrail_output", guardrail_output_node)

    # Node riêng team scan
    graph.add_node("event_classifier", event_classifier_node)
    graph.add_node("hitl_gate_2", hitl_gate_2_node)
    graph.add_node("synthesis_agent", synthesis_node)
    graph.add_node("hitl_gate_1", hitl_gate_1_node)

    graph.add_edge(START, "top_supervisor")
    graph.add_conditional_edges("top_supervisor", route_from_top, ["guardrail_input", "scan_supervisor"])

    # Team chat
    graph.add_conditional_edges("guardrail_input", route_after_guardrail, ["answer", "rewrite_question"])
    graph.add_edge("rewrite_question", "chat_supervisor")
    graph.add_conditional_edges(
        "chat_supervisor", route_by_next, [*CHAT_WORKERS, "scan_supervisor", "concept_retrieval", "answer"]
    )
    graph.add_edge("draw_agent", "chat_supervisor")
    graph.add_edge("portfolio_watch_agent", "chat_supervisor")
    graph.add_edge("concept_retrieval", "answer")
    graph.add_edge("answer", "guardrail_output")
    graph.add_conditional_edges("guardrail_output", route_by_next, ["answer", END])

    # Team scan (cũng phục vụ lấy dữ liệu cho chat_supervisor)
    graph.add_conditional_edges(
        "scan_supervisor", route_by_next, ["price_agent", "news_agent", "eval_agent", *SCAN_STEPS, "chat_supervisor", END]
    )
    graph.add_edge("price_agent", "scan_supervisor")
    graph.add_edge("news_agent", "scan_supervisor")
    for node in SCAN_STEPS:
        graph.add_edge(node, "scan_supervisor")

    # eval_agent dùng chung: báo lại supervisor của team đang chạy
    graph.add_conditional_edges("eval_agent", back_to_team, ["chat_supervisor", "scan_supervisor"])
    return graph


@lru_cache(maxsize=1)
def compile_swarm_graph():
    return build_swarm_graph().compile()





def run_swarm_graph(initial: dict[str, Any], deps: dict[str, Any]) -> tuple[dict[str, Any], list[dict], dict[str, float]]:
    """Chạy graph với deps của request. Trả về (state cuối, chunks từng node, thời gian từng node).

    Mỗi lần chạy = 1 trace gốc Langfuse ("chat" | "scan"); agent_span của các node gắn vào trace này.
    """
    mode = initial.get("mode") or "chat"
    meta: dict[str, Any] = {"turn": initial.get("turn") or "", "user_id": initial.get("user_id"), "kind": mode}
    trace_input = initial.get("question") if mode == "chat" else initial.get("symbol")
    if mode == "scan":
        meta["symbol"] = initial.get("symbol")

    token = graph_deps.set(deps)
    try:
        with trace_request(mode, trace_input, metadata=meta) as root:
            final = dict(initial)
            chunks: list[dict] = []
            node_timings: dict[str, float] = {}
            t_prev = time.perf_counter()
            for chunk in compile_swarm_graph().stream(
                initial,
                config=RunnableConfig(recursion_limit=40),
                stream_mode="updates",
            ):
                elapsed = round(time.perf_counter() - t_prev, 3)
                chunk = {node: values or {} for node, values in chunk.items()}
                chunks.append(chunk)
                for node, values in chunk.items():
                    node_timings[node] = elapsed
                    final.update(values)
                t_prev = time.perf_counter()
            if mode == "chat":
                root["output"] = {"answer": (final.get("answer") or "")[:500], "agents": final.get("completed")}
            else:
                event_routing = final.get("event_routing")
                root["output"] = {
                    "route": str(getattr(getattr(event_routing, "route", None), "value", "")),
                    "gate1_action": final.get("gate1_action"),
                    "gate2_pending": final.get("gate2_pending"),
                }
            if final.get("error"):
                root["error"] = final["error"]
    finally:
        graph_deps.reset(token)
    return final, chunks, node_timings


def list_graph_nodes() -> list[str]:
    return sorted(compile_swarm_graph().get_graph().nodes.keys())


def list_graph_edges() -> list[tuple[str, str]]:
    g = compile_swarm_graph().get_graph()
    return [(str(e.source), str(e.target)) for e in g.edges]



def save_graph_visualization(path: str = "resources/docs/agent_graph.png") -> str:
    """Xuất sơ đồ graph ra PNG (mermaid.ink, cần mạng); lỗi thì ghi Mermaid text (.mmd)."""
    out = path
    if not Path(path).is_absolute():
        out = str(Path(__file__).resolve().parents[4] / path)

    graph = compile_swarm_graph().get_graph()
    try:
        png_bytes = graph.draw_mermaid_png()
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        Path(out).write_bytes(png_bytes)
        return out
    except Exception:
        mmd_path = out.rsplit(".", 1)[0] + ".mmd"
        Path(mmd_path).parent.mkdir(parents=True, exist_ok=True)
        Path(mmd_path).write_text(graph.draw_mermaid(), encoding="utf-8")
        return mmd_path
    
if __name__ == "__main__":
    # python -m ai_backend.infra.agents.graph
    print(save_graph_visualization("resources/docs/agent_graph.png"))
