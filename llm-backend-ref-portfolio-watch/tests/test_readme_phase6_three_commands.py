"""Phase 6 — README ba lệnh chạy AI → Backend → Frontend."""

from __future__ import annotations

from pathlib import Path

README = Path(__file__).resolve().parents[1] / "README.md"


def test_readme_phase6_three_process_commands():
    text = README.read_text(encoding="utf-8")
    assert "Chạy 3 process (Phase 6)" in text
    assert "python scripts/serve_ai.py" in text
    assert "python scripts/serve_backend.py" in text
    assert "python scripts/serve_frontend.py" in text
    assert "8001" in text
    assert "8000" in text
    assert "5173" in text
    assert "http://127.0.0.1:8001/health" in text
    assert "http://127.0.0.1:8000/health" in text
    assert "http://127.0.0.1:5173/" in text
    assert "Frontend → Backend → AI" in text
