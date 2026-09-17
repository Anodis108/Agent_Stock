#!/usr/bin/env python3
"""Phase 10 — StateGraph LangGraph thuần để biểu diễn kiến trúc agent.

Node = từng agent/gate theo specs/agents.md (placeholder pass-through).
Edge = 2 nhánh giám sát + hỏi-đáp (Sơ đồ quan hệ).
Export: PNG (LangGraph, cần mạng) + MMD trung thực từ REQUIRED_* (offline).
Verify: đối chiếu agents.md + ánh xạ portfolio-watch-agent-v4.mmd.

    python scripts/draw_agent_graph.py
    python scripts/draw_agent_graph.py --verify
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DOCS_DIR = ROOT / "docs"
DEFAULT_PNG_PATH = DOCS_DIR / "agent_graph.png"
DEFAULT_MMD_PATH = DOCS_DIR / "agent_graph.mmd"
V4_MMD_PATH = ROOT.parent / "portfolio-watch-agent-v4.mmd"

# Đúng danh sách checklist Phase 10 / specs/agents.md (mục sơ đồ sinh từ code).
REQUIRED_NODES: tuple[str, ...] = (
    "Orchestrator",
    "PriceAgent",
    "NewsAgent",
    "EventClassifier",
    "EvalAgent",
    "SynthesisAgent",
    "Guardrail Output",
    "Confidence Gate",
    "HITL Gate 1",
    "HITL Gate 2",
    "Supervisor",
    "RewriteQuestion",
    "AnswerComposer",
)

# Cạnh kiến trúc (src, dst). END/START dùng hằng LangGraph.
REQUIRED_EDGES: tuple[tuple[str, str], ...] = (
    (START, "Orchestrator"),
    (START, "RewriteQuestion"),
    ("Orchestrator", "PriceAgent"),
    ("Orchestrator", "NewsAgent"),
    ("PriceAgent", "EventClassifier"),
    ("NewsAgent", "EventClassifier"),
    ("EventClassifier", END),
    ("EventClassifier", "EvalAgent"),
    ("EvalAgent", "SynthesisAgent"),
    ("EvalAgent", "HITL Gate 2"),
    ("SynthesisAgent", "Guardrail Output"),
    ("Guardrail Output", "SynthesisAgent"),
    ("Guardrail Output", "Confidence Gate"),
    ("Confidence Gate", END),
    ("Confidence Gate", "HITL Gate 1"),
    ("HITL Gate 1", END),
    ("HITL Gate 2", END),
    ("RewriteQuestion", "Supervisor"),
    ("Supervisor", "PriceAgent"),
    ("Supervisor", "NewsAgent"),
    ("Supervisor", "EvalAgent"),
    ("PriceAgent", "AnswerComposer"),
    ("NewsAgent", "AnswerComposer"),
    ("EvalAgent", "AnswerComposer"),
    ("AnswerComposer", "Guardrail Output"),
    ("Guardrail Output", END),
)

# Ánh xạ node kiến trúc ↔ nhãn chính trên portfolio-watch-agent-v4.mmd (vẽ tay).
V4_LABEL_HINTS: dict[str, tuple[str, ...]] = {
    "Orchestrator": ("Orchestrator giám sát",),
    "PriceAgent": ("PriceAgent", "fetch_latest_close"),
    "NewsAgent": ("NewsAgent", "fetch_cafef_news"),
    "EventClassifier": ("Event Classifier",),
    "EvalAgent": ("EvalAgent",),
    "SynthesisAgent": ("SynthesisAgent",),
    "Guardrail Output": ("Guardrail Output",),
    "Confidence Gate": ("Độ tin cậy",),
    "HITL Gate 1": ("HITL Gate 1",),
    "HITL Gate 2": ("HITL Gate 2",),
    "Supervisor": ("Supervisor",),
    "RewriteQuestion": ("Rewrite Question",),
    "AnswerComposer": ("soạn câu trả lời",),
}


class GraphState(TypedDict, total=False):
    """State tối thiểu — chỉ để visualize, không chạy production."""

    step: str


def _passthrough(state: GraphState) -> dict:
    """Placeholder: không đổi state."""
    return {}


def wire_agent_edges(graph: StateGraph) -> StateGraph:
    """Nối edge 2 nhánh giám sát + hỏi-đáp."""
    for src, dst in REQUIRED_EDGES:
        graph.add_edge(src, dst)
    return graph


def build_agent_graph() -> StateGraph:
    """StateGraph đủ node + edge kiến trúc."""
    graph = StateGraph(GraphState)
    for name in REQUIRED_NODES:
        graph.add_node(name, _passthrough)
    return wire_agent_edges(graph)


def compile_agent_graph():
    """Compile để kiểm tra đồ thị hợp lệ / phục vụ get_graph() PNG."""
    return build_agent_graph().compile()


def list_graph_nodes(graph: StateGraph | None = None) -> list[str]:
    g = graph or build_agent_graph()
    return sorted(g.nodes.keys())


def list_graph_edges(graph: StateGraph | None = None) -> list[tuple[str, str]]:
    """Danh sách (src, dst) đã đăng ký trên builder (chuẩn hoá START/END)."""
    g = graph or build_agent_graph()
    edges: list[tuple[str, str]] = []
    for pair in g.edges:
        if isinstance(pair, tuple) and len(pair) == 2:
            src, dst = pair[0], pair[1]
        else:
            src, dst = pair
        src_s = str(src)
        dst_s = str(dst)
        if src_s in (START, "__start__"):
            src_s = START
        if dst_s in (END, "__end__"):
            dst_s = END
        edges.append((src_s, dst_s))
    return edges


def _mermaid_id(name: str) -> str:
    if name in (START, "__start__"):
        return "__start__"
    if name in (END, "__end__"):
        return "__end__"
    return name.replace(" ", "_")


def architecture_mermaid() -> str:
    """Mermaid trung thực từ REQUIRED_NODES/EDGES (không mất cạnh → END)."""
    lines = [
        "%% Portfolio Watch — architecture graph (Phase 10)",
        "%% Khớp specs/agents.md — 13 agent/gate + 2 nhánh",
        "flowchart TD",
        '  __start__(["START / Cron·Scan·Chat"])',
        '  __end__(["END"])',
    ]
    for name in REQUIRED_NODES:
        lines.append(f'  {_mermaid_id(name)}["{name}"]')
    for src, dst in REQUIRED_EDGES:
        lines.append(f"  {_mermaid_id(src)} --> {_mermaid_id(dst)}")
    return "\n".join(lines) + "\n"


def verify_graph_against_spec(
    *,
    mmd_path: Path | None = None,
    v4_path: Path | None = None,
) -> dict:
    """Đối chiếu StateGraph + docs/*.mmd với agents.md; ánh xạ v4."""
    nodes = set(list_graph_nodes())
    edges = set(list_graph_edges())
    required_n = set(REQUIRED_NODES)
    required_e = set(REQUIRED_EDGES)
    issues: list[str] = []

    if nodes != required_n:
        issues.append(
            f"nodes mismatch missing={required_n - nodes} extra={nodes - required_n}"
        )
    missing_e = required_e - edges
    extra_e = edges - required_e
    if missing_e or extra_e:
        issues.append(f"edges mismatch missing={missing_e} extra={extra_e}")

    branch_checks = {
        "monitor_entry": (START, "Orchestrator") in edges,
        "chat_entry": (START, "RewriteQuestion") in edges,
        "hitl1": ("Confidence Gate", "HITL Gate 1") in edges,
        "hitl2": ("EvalAgent", "HITL Gate 2") in edges,
        "guardrail_shared": ("AnswerComposer", "Guardrail Output") in edges
        and ("SynthesisAgent", "Guardrail Output") in edges,
    }
    for key, ok in branch_checks.items():
        if not ok:
            issues.append(f"branch check failed: {key}")

    mmd_file = mmd_path or DEFAULT_MMD_PATH
    mmd_text = mmd_file.read_text(encoding="utf-8") if mmd_file.is_file() else ""
    if not mmd_text:
        issues.append(f"missing mmd file: {mmd_file}")
    else:
        for name in REQUIRED_NODES:
            if name not in mmd_text and _mermaid_id(name) not in mmd_text:
                issues.append(f"mmd missing node label: {name}")
        for src, dst in REQUIRED_EDGES:
            needle = f"{_mermaid_id(src)} --> {_mermaid_id(dst)}"
            if needle not in mmd_text:
                issues.append(f"mmd missing edge: {needle}")

    v4 = v4_path or V4_MMD_PATH
    v4_hints_ok: dict[str, bool] = {}
    if v4.is_file():
        v4_text = v4.read_text(encoding="utf-8")
        for node, hints in V4_LABEL_HINTS.items():
            v4_hints_ok[node] = any(h in v4_text for h in hints)
            if not v4_hints_ok[node]:
                issues.append(f"v4.mmd thiếu gợi ý cho {node}: {hints}")
    else:
        issues.append(f"v4.mmd not found: {v4}")

    return {
        "ok": not issues,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "required_nodes": len(REQUIRED_NODES),
        "required_edges": len(REQUIRED_EDGES),
        "branch_checks": branch_checks,
        "v4_hints_ok": v4_hints_ok,
        "issues": issues,
        "note": (
            "v4.mmd chi tiết hơn (tool/store); đối chiếu theo 13 agent/gate "
            "kiến trúc ở agents.md — không so tuyệt đối số node v4."
        ),
    }


def save_graph_visualization(path: str | Path | None = None) -> str:
    """PNG qua LangGraph; MMD trung thực từ REQUIRED_* (offline, đủ cạnh END)."""
    png_path = Path(path) if path is not None else DEFAULT_PNG_PATH
    if not png_path.is_absolute():
        png_path = ROOT / png_path
    if png_path.suffix.lower() != ".png":
        png_path = png_path.with_suffix(".png")
    mmd_path = png_path.with_suffix(".mmd")
    png_path.parent.mkdir(parents=True, exist_ok=True)

    mmd_path.write_text(architecture_mermaid(), encoding="utf-8")

    try:
        g = compile_agent_graph().get_graph(xray=True)
        png_path.write_bytes(g.draw_mermaid_png())
        return str(png_path)
    except Exception:
        return str(mmd_path)


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="Draw / verify Portfolio Watch agent graph")
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Đối chiếu node/cạnh với agents.md + ánh xạ v4.mmd",
    )
    args = parser.parse_args(argv)

    nodes = list_graph_nodes()
    edges = list_graph_edges()
    print(f"StateGraph nodes ({len(nodes)}):")
    for n in nodes:
        print(f"  - {n}")
    print(f"StateGraph edges ({len(edges)}):")
    for s, d in edges:
        print(f"  - {s!r} → {d!r}")

    saved = save_graph_visualization()
    mmd = Path(saved).with_suffix(".mmd") if str(saved).endswith(".png") else Path(saved)
    if str(saved).endswith(".png"):
        print(f"PNG: {saved}")
    print(f"MMD: {mmd}")

    report = verify_graph_against_spec(mmd_path=mmd if mmd.is_file() else DEFAULT_MMD_PATH)
    print(
        f"Verify: nodes={report['node_count']}/{report['required_nodes']} "
        f"edges={report['edge_count']}/{report['required_edges']} "
        f"ok={report['ok']}"
    )
    print(report["note"])
    if report["issues"]:
        for issue in report["issues"]:
            print(f"  - {issue}")
        return 1
    msg = (
        "VERIFY_OK: khớp agents.md (13 node) + 2 nhánh + 2 HITL; ánh xạ v4 OK."
        if args.verify
        else "OK: đủ node + edge + visualization; đối chiếu spec pass."
    )
    print(msg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
