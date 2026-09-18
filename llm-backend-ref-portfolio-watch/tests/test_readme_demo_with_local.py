"""SDD — README Demo with local (FE/BE local, ngrok optional, config.js)."""

from __future__ import annotations

from pathlib import Path

README = Path(__file__).resolve().parents[1] / "README.md"


def test_readme_demo_with_local_section():
    text = README.read_text(encoding="utf-8")
    assert "## Demo with local" in text
    assert "### Start Frontend locally" in text
    assert "### Start Backend locally" in text
    assert "python scripts/serve_frontend.py" in text
    assert "python scripts/serve_backend.py" in text
    assert "python scripts/serve_ai.py" in text
    assert "### Expose Frontend on local" in text
    assert "http://127.0.0.1:5173/" in text
    assert "8000" in text and "8001" in text
    assert "### Configure Frontend" in text or "Configure Frontend" in text
    assert "frontend/config.js" in text
    assert "?backend=" in text
    assert "### Expose Backend with ngrok" in text or "ngrok http 8000" in text
