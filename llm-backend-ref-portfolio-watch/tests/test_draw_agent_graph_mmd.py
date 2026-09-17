"""Phase 10 — fallback / offline MMD (architecture_mermaid)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "draw_agent_graph.py"


def _load():
    name = "draw_agent_graph_mmd"
    spec = importlib.util.spec_from_file_location(name, SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_save_always_writes_mmd_and_png_when_ok(tmp_path: Path, monkeypatch) -> None:
    mod = _load()
    mock_g = MagicMock()
    mock_g.draw_mermaid_png.return_value = b"\x89PNG\r\n"
    mock_compiled = MagicMock()
    mock_compiled.get_graph.return_value = mock_g
    monkeypatch.setattr(mod, "compile_agent_graph", lambda: mock_compiled)

    out = tmp_path / "agent_graph.png"
    result = mod.save_graph_visualization(out)
    assert Path(result) == out
    assert out.read_bytes().startswith(b"\x89PNG")
    mmd = out.with_suffix(".mmd")
    assert mmd.is_file()
    assert "Orchestrator" in mmd.read_text(encoding="utf-8")
    assert "HITL_Gate_1 --> __end__" in mmd.read_text(encoding="utf-8")


def test_save_falls_back_to_mmd_when_png_fails(tmp_path: Path, monkeypatch) -> None:
    mod = _load()
    mock_g = MagicMock()
    mock_g.draw_mermaid_png.side_effect = RuntimeError("mermaid.ink down")
    mock_compiled = MagicMock()
    mock_compiled.get_graph.return_value = mock_g
    monkeypatch.setattr(mod, "compile_agent_graph", lambda: mock_compiled)

    out = tmp_path / "agent_graph.png"
    result = mod.save_graph_visualization(out)
    assert result.endswith(".mmd")
    text = Path(result).read_text(encoding="utf-8")
    assert "flowchart TD" in text
    assert "Orchestrator" in text
    assert not out.is_file()


def test_default_mmd_path() -> None:
    mod = _load()
    assert mod.DEFAULT_MMD_PATH == ROOT / "docs" / "agent_graph.mmd"


def test_checklist_mmd_fallback_checked() -> None:
    text = (ROOT / "specs" / "implementation-plan.md").read_text(encoding="utf-8")
    assert "- [x] Fallback khi không có mạng (mermaid.ink lỗi):" in text
