"""Phase 6 — README local run (mở rộng dần theo từng item plan)."""

from __future__ import annotations

from pathlib import Path

README = Path(__file__).resolve().parents[1] / "README.md"


def test_readme_local_run_covers_phase6_checklist():
    text = README.read_text(encoding="utf-8")
    assert "Prerequisites (Phase 6)" in text
    assert "Chạy 3 process (Phase 6)" in text
    assert "Biến môi trường (Phase 6)" in text
    assert "Eval (Phase 6)" in text
    assert "Troubleshooting (Phase 6)" in text
    assert "pip install -e" in text
    assert ".env.example" in text
    assert "OPENAI_API_KEYS" in text
    assert "dong312" in text
    assert "serve_ai.py" in text
    assert "serve_backend.py" in text
    assert "serve_frontend.py" in text
    assert "AI_BASE_URL" in text
    assert "FRONTEND_ORIGIN" in text
    assert "--case-id" in text
    assert "run_eval.py" in text
    assert "CORS" in text
    assert "AI timeout" in text
    assert "8000" in text
    assert "8001" in text
    assert "5173" in text
