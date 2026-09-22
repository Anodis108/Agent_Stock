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


def test_phase10_claude_layout():
    html = (FE / "index.html").read_text(encoding="utf-8")
    css = (FE / "style.css").read_text(encoding="utf-8")
    js = (FE / "app.js").read_text(encoding="utf-8")

    # Left conversation column + composer at bottom
    assert "chat-column" in html
    assert "chat-messages" in html
    assert "composer-container" in html
    assert "chat-form" in html
    assert "chat-input" in html
    assert "chat-send" in html

    # Error banner and network error handling
    assert "chat-error-banner" in html
    assert "formatApiError" in js
    assert "showChatErrorBanner" in js

    # Secondary column and tabbed navigation for preserved features
    assert "secondary-column" in html
    assert "secondary-tabs" in html
    assert "tab-btn" in html

    # CSS styles
    assert ".chat-column" in css
    assert ".composer-container" in css
    assert ".chat-error-banner" in css


def test_phase11_live_graph_and_hover_io():
    html = (FE / "index.html").read_text(encoding="utf-8")
    css = (FE / "style.css").read_text(encoding="utf-8")
    js = (FE / "app.js").read_text(encoding="utf-8")

    # Live graph panel replacing placeholder
    assert "live-graph-panel" in html
    assert "graph-nodes-flow" in html
    assert "graph-node-inspector" in html
    assert "inspector-input-content" in html
    assert "inspector-output-content" in html
    assert "graph-placeholder-card" not in html

    # Live graph styling
    assert ".live-graph-panel" in css
    assert ".graph-node-card" in css
    assert ".graph-node-inspector" in css
    assert "node-glow-pulse" in css

    # App.js live graph & I/O logic
    assert "PW_renderLiveGraph" in js
    assert "PW_animateLiveGraph" in js
    assert "PW_showNodeInspector" in js
    assert "showNodeInspector" in js
    assert "step.input" in js and "step.output" in js
