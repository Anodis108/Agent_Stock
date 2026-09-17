"""Phase 10 — đối chiếu sơ đồ sinh ra với agents.md / v4.mmd."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "draw_agent_graph.py"


def _load():
    name = "draw_agent_graph_verify"
    spec = importlib.util.spec_from_file_location(name, SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_architecture_mermaid_has_all_nodes_and_end_edges() -> None:
    mod = _load()
    text = mod.architecture_mermaid()
    for name in mod.REQUIRED_NODES:
        assert name in text
    assert "__start__ --> Orchestrator" in text
    assert "__start__ --> RewriteQuestion" in text
    assert "EventClassifier --> __end__" in text
    assert "Confidence_Gate --> __end__" in text
    assert "Guardrail_Output --> __end__" in text
    assert "HITL_Gate_1 --> __end__" in text
    assert "HITL_Gate_2 --> __end__" in text


def test_verify_graph_against_spec_passes(tmp_path: Path) -> None:
    mod = _load()
    mmd = tmp_path / "agent_graph.mmd"
    mmd.write_text(mod.architecture_mermaid(), encoding="utf-8")
    report = mod.verify_graph_against_spec(mmd_path=mmd)
    assert report["ok"] is True, report["issues"]
    assert report["node_count"] == 13
    assert report["edge_count"] == len(mod.REQUIRED_EDGES)
    assert report["branch_checks"]["monitor_entry"]
    assert report["branch_checks"]["chat_entry"]
    assert report["branch_checks"]["hitl1"]
    assert report["branch_checks"]["hitl2"]
    assert all(report["v4_hints_ok"].values()), report["v4_hints_ok"]


def test_verify_detects_missing_mmd_edge(tmp_path: Path) -> None:
    mod = _load()
    mmd = tmp_path / "agent_graph.mmd"
    # thiếu cạnh HITL
    broken = "\n".join(
        line
        for line in mod.architecture_mermaid().splitlines()
        if "HITL_Gate_1 --> __end__" not in line
    )
    mmd.write_text(broken + "\n", encoding="utf-8")
    report = mod.verify_graph_against_spec(mmd_path=mmd)
    assert report["ok"] is False
    assert any("HITL_Gate_1 --> __end__" in i for i in report["issues"])


def test_checklist_verify_checked() -> None:
    text = (ROOT / "specs" / "implementation-plan.md").read_text(encoding="utf-8")
    assert "- [x] Đối chiếu thủ công: số node + cạnh trong sơ đồ sinh ra khớp với" in text
