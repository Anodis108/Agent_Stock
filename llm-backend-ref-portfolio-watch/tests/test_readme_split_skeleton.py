"""Phase 1/6 — README documents 3 process ports + lệnh chạy."""

from __future__ import annotations

from pathlib import Path

README = Path(__file__).resolve().parents[1] / "README.md"


def test_readme_skeleton_documents_three_process_ports():
    text = README.read_text(encoding="utf-8")
    assert "Chạy 3 process (Phase 6)" in text
    assert "8001" in text
    assert "8000" in text
    assert "5173" in text
    assert "AI_BASE_URL" in text
    assert "serve_ai.py" in text
    assert "serve_backend.py" in text
    assert "serve_frontend.py" in text
    assert "Frontend → Backend → AI" in text
    assert "Phase 6" in text
