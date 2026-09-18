"""Phase 6 — README prerequisites (conda dong312 / venv + .env)."""

from __future__ import annotations

from pathlib import Path

README = Path(__file__).resolve().parents[1] / "README.md"


def test_readme_phase6_prerequisites():
    text = README.read_text(encoding="utf-8")
    assert "Prerequisites (Phase 6)" in text
    assert "dong312" in text
    assert ".env.example" in text
    assert "OPENAI_API_KEYS" in text
    assert "pip install -e" in text
    assert "3.10" in text
    # Hai lựa chọn môi trường
    assert "conda activate" in text
    assert "venv" in text.lower()
    assert "Copy-Item" in text or "cp .env.example" in text
