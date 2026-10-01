"""LangGraph mô tả luồng agent THẬT — khớp `scan_symbol` + `answer_question`.

Node = bước tương ứng trong application layer (tên trùng `agent_span`).
Conditional edge = hàm routing thật từ production (`should_auto_send`, `_is_abnormal`, …).
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from backend.application.scan_symbol import (
    _has_gate2_proposal,
    _is_abnormal,
    should_auto_send,
)
from backend.agents.price_agent import PriceAgentResult
from backend.domain.entities import RoutingDecision, Severity

# Tên node = bước thật trong code (agent_span / luồng application).
SCAN_NODES = (
    "orchestrator",
    "price_agent",
    "news_agent",
    "event_classifier",
    "eval_agent",
    "synthesis_agent",
    "guardrail_output",
    "confidence_gate",
    "hitl_gate_1",
    "hitl_gate_2",
)
CHAT_NODES = ("rewrite_question", "supervisor", "answer_composer")
ALL_NODES = SCAN_NODES + CHAT_NODES


class PortfolioState(TypedDict, total=False):
    """State tối thiểu cho routing — field khớp dữ liệu luồng thật."""

    branch: Literal["scan", "chat"]
    routing: RoutingDecision | None
    severity: Severity | None
    price_change_pct: float | None
    threshold_pct: float
    guardrail_ok: bool


def _passthrough(_state: PortfolioState) -> dict:
    return {}


def _route_after_classifier(state: PortfolioState) -> Literal["eval_agent", "__end__"]:
    routing = state.get("routing")
    if routing is None:
        return END
    return "eval_agent" if _is_abnormal(routing.route) else END


def _route_after_eval_scan(state: PortfolioState) -> Literal["synthesis_agent", "hitl_gate_2"]:
    severity = state.get("severity")
    if severity is not None and _has_gate2_proposal(severity):
        return "hitl_gate_2"
    return "synthesis_agent"


def _route_guardrail(
    state: PortfolioState,
) -> Literal["confidence_gate", "synthesis_agent", "__end__"]:
    if state.get("branch") == "chat":
        return END
    if not state.get("guardrail_ok", True):
        return "synthesis_agent"
    return "confidence_gate"


def _route_confidence_gate(state: PortfolioState) -> Literal["__end__", "hitl_gate_1"]:
    severity = state.get("severity")
    change = state.get("price_change_pct")
    thr = state.get("threshold_pct") or 3.0
    if severity is None or change is None:
        return "hitl_gate_1"
    price = PriceAgentResult(
        symbol="",
        latest_close=None,
        prev_close=None,
        change_pct=change,
    )
    return END if should_auto_send(severity, price, thr) else "hitl_gate_1"


def build_portfolio_graph() -> StateGraph:
    """StateGraph 2 nhánh — cấu trúc khớp specs/agents.md + application layer."""
    graph = StateGraph(PortfolioState)

    for name in ALL_NODES:
        graph.add_node(name, _passthrough)

    # ── Nhánh giám sát: scan_watchlist → scan_symbol ──
    graph.add_edge(START, "orchestrator")
    graph.add_edge("orchestrator", "price_agent")
    graph.add_edge("orchestrator", "news_agent")
    graph.add_edge("price_agent", "event_classifier")
    graph.add_edge("news_agent", "event_classifier")
    graph.add_conditional_edges(
        "event_classifier",
        _route_after_classifier,
        {"eval_agent": "eval_agent", END: END},
    )
    graph.add_conditional_edges(
        "eval_agent",
        _route_after_eval_scan,
        {"synthesis_agent": "synthesis_agent", "hitl_gate_2": "hitl_gate_2"},
    )
    graph.add_edge("hitl_gate_2", END)
    graph.add_edge("synthesis_agent", "guardrail_output")
    graph.add_conditional_edges(
        "guardrail_output",
        _route_guardrail,
        {
            "confidence_gate": "confidence_gate",
            "synthesis_agent": "synthesis_agent",
            END: END,
        },
    )
    graph.add_conditional_edges(
        "confidence_gate",
        _route_confidence_gate,
        {END: END, "hitl_gate_1": "hitl_gate_1"},
    )
    graph.add_edge("hitl_gate_1", END)

    # ── Nhánh hỏi-đáp: answer_question ──
    graph.add_edge(START, "rewrite_question")
    graph.add_edge("rewrite_question", "supervisor")
    graph.add_edge("supervisor", "price_agent")
    graph.add_edge("supervisor", "news_agent")
    graph.add_edge("supervisor", "eval_agent")
    graph.add_edge("price_agent", "answer_composer")
    graph.add_edge("news_agent", "answer_composer")
    graph.add_edge("eval_agent", "answer_composer")
    graph.add_edge("answer_composer", "guardrail_output")

    return graph


@lru_cache(maxsize=1)
def compile_portfolio_graph():
    return build_portfolio_graph().compile()


def list_graph_nodes() -> list[str]:
    return sorted(compile_portfolio_graph().get_graph(xray=True).nodes.keys())


def list_graph_edges() -> list[tuple[str, str]]:
    g = compile_portfolio_graph().get_graph(xray=True)
    edges: list[tuple[str, str]] = []
    for edge in g.edges:
        src = edge.source if hasattr(edge, "source") else edge[0]
        dst = edge.target if hasattr(edge, "target") else edge[1]
        s = START if str(src) in ("__start__", START) else str(src)
        d = END if str(dst) in ("__end__", END) else str(dst)
        edges.append((s, d))
    return edges


def save_graph_visualization(path: str = "resources/docs/agent_graph.png") -> str:
    """Xuất sơ đồ graph ra file — hữu ích để debug/trình bày cấu trúc agent.

    Thử vẽ PNG trước (draw_mermaid_png — gọi API mermaid.ink, cần mạng).
    Nếu không có mạng/lỗi, fallback ghi ra Mermaid text thuần (.mmd, không cần mạng) —
    dán vào https://mermaid.live hoặc preview trực tiếp trong VSCode/GitHub.

    Returns:
        Đường dẫn file thực sự đã ghi (có thể khác `path` nếu fallback sang .mmd).
    """
    from pathlib import Path

    out = path
    if not Path(path).is_absolute():
        out = str(Path(__file__).resolve().parents[4] / path)

    graph = compile_portfolio_graph().get_graph()

    try:
        png_bytes = graph.draw_mermaid_png()
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        with open(out, "wb") as f:
            f.write(png_bytes)
        return out
    except Exception:
        mmd_path = out.rsplit(".", 1)[0] + ".mmd"
        Path(mmd_path).parent.mkdir(parents=True, exist_ok=True)
        with open(mmd_path, "w", encoding="utf-8") as f:
            f.write(graph.draw_mermaid())
        return mmd_path


if __name__ == "__main__":
    # python -m backend.domain.graph.workflow
    saved = save_graph_visualization("docs/agent_graph.png")
    print(saved)
