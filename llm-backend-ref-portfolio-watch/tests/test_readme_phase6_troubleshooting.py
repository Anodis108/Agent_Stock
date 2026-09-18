"""Phase 6 — README troubleshooting (key, port, AI, CORS)."""

from __future__ import annotations

from pathlib import Path

README = Path(__file__).resolve().parents[1] / "README.md"


def test_readme_phase6_troubleshooting():
    text = README.read_text(encoding="utf-8")
    assert "Troubleshooting (Phase 6)" in text
    assert "OPENAI_API_KEYS" in text
    assert "Port trùng" in text or "port trùng" in text.lower()
    assert "8000" in text and "8001" in text and "5173" in text
    assert "AI không kết nối được" in text or "unreachable" in text.lower()
    assert "AI timeout" in text
    assert "CORS" in text
    assert "FRONTEND_ORIGIN" in text
    assert "502" in text
