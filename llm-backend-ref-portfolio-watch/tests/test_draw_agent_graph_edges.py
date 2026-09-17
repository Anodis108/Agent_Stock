"""Phase 10 — wire edges 2 nhánh trên draw_agent_graph StateGraph."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "draw_agent_graph.py"


def _load():
    name = "draw_agent_graph_edges"
    spec = importlib.util.spec_from_file_location(name, SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_required_edges_cover_both_branches() -> None:
    mod = _load()
    edges = set(mod.REQUIRED_EDGES)
    # Giám sát
    assert (mod.START, "Orchestrator") in edges
    assert ("Orchestrator", "PriceAgent") in edges
    assert ("Orchestrator", "NewsAgent") in edges
    assert ("PriceAgent", "EventClassifier") in edges
    assert ("NewsAgent", "EventClassifier") in edges
    assert ("EventClassifier", mod.END) in edges
    assert ("EventClassifier", "EvalAgent") in edges
    assert ("EvalAgent", "SynthesisAgent") in edges
    assert ("EvalAgent", "HITL Gate 2") in edges
    assert ("SynthesisAgent", "Guardrail Output") in edges
    assert ("Guardrail Output", "Confidence Gate") in edges
    assert ("Confidence Gate", "HITL Gate 1") in edges
    assert ("HITL Gate 1", mod.END) in edges
    assert ("HITL Gate 2", mod.END) in edges
    # Hỏi-đáp
    assert (mod.START, "RewriteQuestion") in edges
    assert ("RewriteQuestion", "Supervisor") in edges
    assert ("Supervisor", "PriceAgent") in edges
    assert ("AnswerComposer", "Guardrail Output") in edges
    assert ("Guardrail Output", mod.END) in edges


def test_build_registers_all_required_edges() -> None:
    mod = _load()
    got = set(mod.list_graph_edges())
    missing = [e for e in mod.REQUIRED_EDGES if e not in got]
    assert missing == [], missing


def test_compile_agent_graph_succeeds() -> None:
    mod = _load()
    compiled = mod.compile_agent_graph()
    assert compiled is not None


def test_checklist_edges_checked() -> None:
    text = (ROOT / "specs" / "implementation-plan.md").read_text(encoding="utf-8")
    assert "- [x] Nối edge giữa các node đúng luồng dữ liệu ở 2 nhánh" in text
