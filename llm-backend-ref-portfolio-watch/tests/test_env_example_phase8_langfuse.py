"""Phase 8 — .env.example đủ biến Langfuse + ghi chú bật monitoring."""

from __future__ import annotations

from pathlib import Path

ENV_EXAMPLE = Path(__file__).resolve().parents[1] / ".env.example"


def test_env_example_langfuse_vars_complete():
    text = ENV_EXAMPLE.read_text(encoding="utf-8")
    for key in (
        "MONITORING_ENABLED",
        "LANGFUSE_PUBLIC_KEY",
        "LANGFUSE_SECRET_KEY",
        "LANGFUSE_HOST",
    ):
        assert f"{key}=" in text, f"missing assignment {key}="
    assert "MONITORING_ENABLED=false" in text
    assert "https://cloud.langfuse.com" in text
    # Không nhúng secret mẫu thật (assignment)
    assert "LANGFUSE_SECRET_KEY=sk" not in text
    assert "LANGFUSE_PUBLIC_KEY=pk-lf-" not in text
    # Ghi chú Phase 8 / cách bật
    assert "Phase 8" in text or "Langfuse" in text
    assert "no-op" in text.lower() or "Tắt mặc định" in text
    assert "pip install langfuse" in text
    assert "localhost:3000" in text or "self-host" in text.lower() or "Self-host" in text
