"""Phase 8 — README: bật monitoring, mở Langfuse, tìm trace theo câu hỏi / request id."""

from __future__ import annotations

from pathlib import Path

README = Path(__file__).resolve().parents[1] / "README.md"


def test_readme_langfuse_enable_open_find_trace():
    text = README.read_text(encoding="utf-8")
    assert "## Langfuse (Phase 8)" in text
    assert "### Bật monitoring" in text
    assert "MONITORING_ENABLED=true" in text
    assert "LANGFUSE_PUBLIC_KEY" in text
    assert "LANGFUSE_SECRET_KEY" in text
    assert "LANGFUSE_HOST" in text
    assert "pip install langfuse" in text
    assert "### Mở Langfuse" in text
    assert "### Tìm trace theo câu hỏi / request id" in text
    assert "request_id" in text
    assert 'name **`chat`**' in text or "name=`chat`" in text or "**`chat`**" in text
    assert "phase8_langfuse_e2e.py" in text
    assert "### Troubleshooting monitoring" in text
