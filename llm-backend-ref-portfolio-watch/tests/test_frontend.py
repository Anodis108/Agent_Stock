"""Frontend static — scaffold + gọi Backend."""

from __future__ import annotations

from pathlib import Path

FE = Path(__file__).resolve().parents[1] / "src" / "portfolio_watch" / "frontend"


def test_frontend_files_and_sections():
    for name in ("index.html", "app.js", "style.css", "config.js"):
        assert (FE / name).is_file()
    html = (FE / "index.html").read_text(encoding="utf-8")
    for sid in ("chat", "timeline", "watchlist", "approvals"):
        assert f'id="{sid}"' in html


def test_frontend_calls_backend_not_ai():
    js = (FE / "app.js").read_text(encoding="utf-8")
    cfg = (FE / "config.js").read_text(encoding="utf-8")
    assert "BACKEND_BASE_URL" in cfg
    assert "/chat" in js and "/v1/chat" not in js
    assert "8001" not in js
    assert "MOCK_STEPS" not in js
