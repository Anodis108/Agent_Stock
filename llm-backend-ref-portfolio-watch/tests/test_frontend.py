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

def test_phase13_single_origin_wiring():
    js = (FE / "app.js").read_text(encoding="utf-8")
    for ep in ("/chat", "/scan", "/market", "/watchlist", "/approvals"):
        assert ep in js
    assert "8001" not in js
    assert "/v1/" not in js


def test_phase13_no_separate_ai_from_frontend():
    """Product gộp: browser không gọi AI service :8001 / /v1/*."""
    js = (FE / "app.js").read_text(encoding="utf-8")
    cfg = (FE / "config.js").read_text(encoding="utf-8")
    assert "8001" not in js
    assert "/v1/" not in js
    assert "AI_BASE_URL" not in js
    assert "AI_TRANSPORT" not in js
    assert "BACKEND_BASE_URL" in cfg
    assert 'BACKEND_BASE_URL: ""' in cfg or "BACKEND_BASE_URL: ''" in cfg


def test_phase13_scan_approve_ui_wiring():
    """Flow C: quét + approve/reject từ UI mới (app.js)."""
    js = (FE / "app.js").read_text(encoding="utf-8")
    html = (FE / "index.html").read_text(encoding="utf-8")

    for fn in ("doScan", "doApprove", "doReject", "loadApprovals", "loadMarket"):
        assert fn in js
    assert 'api("POST", "/scan"' in js
    assert '"/approvals/"' in js and "/approve" in js and "/reject" in js
    # Refresh panels sau hành động (không reload trang)
    assert "loadApprovals()" in js
    assert "loadMarket()" in js
    assert "location.reload" not in js
    assert "scan-form" in html
    assert "approvals-list" in html


def test_phase14_diagram_ui_render():
    """Phase 14: UI render sơ đồ trong bubble hoặc panel."""
    html = (FE / "index.html").read_text(encoding="utf-8")
    css = (FE / "style.css").read_text(encoding="utf-8")
    js = (FE / "app.js").read_text(encoding="utf-8")

    assert "mermaid.min.js" in html
    assert "renderMermaidInElement" in js
    assert "initMermaid" in js
    assert "data.diagram" in js
    assert "PW_renderMermaidInElement" in js
    assert ".mermaid-diagram" in css
    assert ".diagram-panel" in css


def test_phase16_error_resilience_ui():
    """Phase 16 line 1: UI error resilience (no blank page on failure)."""
    html = (FE / "index.html").read_text(encoding="utf-8")
    js = (FE / "app.js").read_text(encoding="utf-8")

    assert 'id="watchlist-error"' in html
    assert 'id="approvals-error"' in html
    assert 'id="scan-error"' in html

    assert "allSettled" in js or "safeLoadWatchlist" in js
    assert "showApprovalsError" in js
    assert 'addEventListener("error"' in js
    assert 'addEventListener("unhandledrejection"' in js
    assert "location.reload" not in js
