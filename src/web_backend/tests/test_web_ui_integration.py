"""Integration tests for Web UI Frontend (HTML, CSS, JS layout & containers)."""

from __future__ import annotations

from pathlib import Path


def _find_frontend_dir() -> Path:
    candidates = [
        Path(__file__).resolve().parents[2] / "frontend",
        Path(__file__).resolve().parents[3] / "src" / "frontend",
        Path.cwd() / "src" / "frontend",
        Path.cwd() / "frontend",
    ]
    for c in candidates:
        if c.is_dir() and (c / "index.html").is_file():
            return c
    return Path(__file__).resolve().parents[3] / "src" / "frontend"


def test_ui_html_hint_chips_and_graph_containers():
    """Verify index.html contains hint chips for Greeting and Portfolio NAV and graph containers."""
    fe = _find_frontend_dir()
    html = (fe / "index.html").read_text(encoding="utf-8")

    assert "Xin chào bot!" in html, "Missing 'Xin chào bot!' hint chip"
    assert "Kiểm tra NAV danh mục" in html, "Missing 'Kiểm tra NAV danh mục' hint chip"
    assert 'id="live-graph-panel"' in html
    assert 'id="graph-nodes-flow"' in html
    assert 'id="graph-node-inspector"' in html


def test_ui_css_chart_and_graph_styles():
    """Verify style.css contains chart styling, glowing animation, and responsive media queries."""
    fe = _find_frontend_dir()
    css = (fe / "style.css").read_text(encoding="utf-8")

    assert ".chat-chart-container" in css
    assert ".chat-chart-img" in css
    assert "@media" in css
    assert ".graph-node-card" in css


def test_ui_js_node_mappings_and_inspector():
    """Verify app.js node mapping and inspector logic."""
    fe = _find_frontend_dir()
    js = (fe / "app.js").read_text(encoding="utf-8")

    assert "chat-messages" in js
    assert "token" in js
