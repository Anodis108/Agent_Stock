"""Phase 10 — save_graph_visualization → docs/agent_graph.png."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "draw_agent_graph.py"


def _load():
    name = "draw_agent_graph_png"
    spec = importlib.util.spec_from_file_location(name, SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_save_graph_visualization_writes_png(tmp_path: Path, monkeypatch) -> None:
    mod = _load()
    fake_png = b"\x89PNG\r\n\x1a\nfake"

    mock_g = MagicMock()
    mock_g.draw_mermaid_png.return_value = fake_png
    mock_compiled = MagicMock()
    mock_compiled.get_graph.return_value = mock_g
    monkeypatch.setattr(mod, "compile_agent_graph", lambda: mock_compiled)

    out = tmp_path / "agent_graph.png"
    result = mod.save_graph_visualization(out)
    assert Path(result) == out
    assert out.read_bytes() == fake_png
    assert out.with_suffix(".mmd").is_file()
    mock_compiled.get_graph.assert_called_once_with(xray=True)
    mock_g.draw_mermaid_png.assert_called_once()


def test_default_png_path_is_docs_agent_graph() -> None:
    mod = _load()
    assert mod.DEFAULT_PNG_PATH == ROOT / "docs" / "agent_graph.png"


def test_checklist_png_checked() -> None:
    text = (ROOT / "specs" / "implementation-plan.md").read_text(encoding="utf-8")
    assert (
        "- [x] Tái dùng pattern `save_graph_visualization` từ"
        in text
    )
