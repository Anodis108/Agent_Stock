"""Phase 10 — draw_agent_graph StateGraph nodes (placeholder)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "draw_agent_graph.py"


def _load():
    name = "draw_agent_graph_nodes"
    spec = importlib.util.spec_from_file_location(name, SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_required_nodes_match_agents_spec() -> None:
    mod = _load()
    expected = {
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
    }
    assert set(mod.REQUIRED_NODES) == expected
    assert len(mod.REQUIRED_NODES) == 13


def test_build_agent_graph_registers_all_nodes() -> None:
    mod = _load()
    graph = mod.build_agent_graph()
    nodes = set(mod.list_graph_nodes(graph))
    assert nodes == set(mod.REQUIRED_NODES)


def test_passthrough_placeholder() -> None:
    mod = _load()
    assert mod._passthrough({"step": "x"}) == {}


def test_checklist_draw_agent_graph_nodes_checked() -> None:
    text = (ROOT / "specs" / "implementation-plan.md").read_text(encoding="utf-8")
    assert "- [x] `scripts/draw_agent_graph.py` — build 1 `StateGraph`" in text
