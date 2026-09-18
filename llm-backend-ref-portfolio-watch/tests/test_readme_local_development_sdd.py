"""SDD Bước 9 — README local development (prereq, install, env, run, URLs, troubleshoot)."""

from __future__ import annotations

from pathlib import Path

README = Path(__file__).resolve().parents[1] / "README.md"


def test_readme_local_development_sdd_step9():
    text = README.read_text(encoding="utf-8")
    assert "## Local development" in text
    assert "### Prerequisites" in text
    assert "### Install" in text
    assert 'pip install -e ".[dev]"' in text or "pip install -e" in text
    assert "### Environment variables" in text
    assert ".env.example" in text
    assert "OPENAI_API_KEYS" in text
    assert "### Run — Backend" in text or "serve_backend.py" in text
    assert "### Run — Frontend" in text or "serve_frontend.py" in text
    assert "python scripts/serve_ai.py" in text
    assert "python scripts/serve_backend.py" in text
    assert "python scripts/serve_frontend.py" in text
    assert "### Local URLs" in text
    assert "http://127.0.0.1:5173/" in text
    assert "http://127.0.0.1:8000/health" in text
    assert "http://127.0.0.1:8001/health" in text
    assert "### Troubleshooting" in text or "Troubleshooting (tóm tắt)" in text
    assert "CORS" in text
    # Không còn status Phase 8 «chưa làm»
    assert "Phase 8 còn lại" not in text
