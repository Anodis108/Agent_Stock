"""Phase 6 — README bảng biến môi trường bắt buộc / tuỳ chọn."""

from __future__ import annotations

from pathlib import Path

README = Path(__file__).resolve().parents[1] / "README.md"


def test_readme_phase6_env_table():
    text = README.read_text(encoding="utf-8")
    assert "Biến môi trường (Phase 6)" in text
    assert "Bắt buộc" in text
    assert "Tuỳ chọn" in text or "Tùy chọn" in text
    assert "OPENAI_API_KEYS" in text
    assert "LLM_BACKEND" in text
    assert "AI_BASE_URL" in text
    assert "FRONTEND_ORIGIN" in text
    assert "BACKEND_SQLITE_PATH" in text
    assert "SQLITE_PATH" in text
    assert ".env.example" in text
