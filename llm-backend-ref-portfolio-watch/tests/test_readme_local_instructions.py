"""Phase 6 — README local run instructions có đủ mục implementation-plan."""

from __future__ import annotations

from pathlib import Path

README = Path(__file__).resolve().parents[1] / "README.md"


def test_readme_local_run_covers_phase6_checklist():
    text = README.read_text(encoding="utf-8")
    assert "Chạy local (Phase 6)" in text
    assert "pip install -e ." in text
    assert ".env.example" in text
    assert "OPENAI_API_KEYS" in text
    assert "SQLITE_PATH" in text or "sqlite" in text.lower()
    assert "python -m src.portfolio_watch.main" in text
    assert "uvicorn src.portfolio_watch.main:app" in text
    assert "8000" in text
    assert "http://127.0.0.1:8000" in text
    assert "/health" in text
    assert "connect(settings.sqlite_path)" in text or "sqlite_db" in text
    # UI cùng origin
    assert "cùng origin" in text
    # Cron thủ công
    assert "scan_watchlist" in text
    assert "/scan" in text
    assert "/chat" in text
    assert "/approvals" in text
    assert "Copy-Item" in text or "Windows" in text
