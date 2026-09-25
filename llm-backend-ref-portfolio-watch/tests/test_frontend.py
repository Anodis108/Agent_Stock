"""Frontend static — scaffold + gọi Backend."""

from __future__ import annotations

from pathlib import Path

FE = Path(__file__).resolve().parents[1] / "src" / "frontend"
if not FE.is_dir():
    FE = Path(__file__).resolve().parents[1] / "frontend"
if not FE.is_dir():
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


def test_phase3_session_sidebar_ui():
    """Phase 3: Session management sidebar and chat switching."""
    html = (FE / "index.html").read_text(encoding="utf-8")
    css = (FE / "style.css").read_text(encoding="utf-8")
    js = (FE / "app.js").read_text(encoding="utf-8")

    # HTML elements
    assert 'id="session-sidebar"' in html
    assert 'id="btn-new-session"' in html
    assert 'id="session-list"' in html
    assert 'id="active-session-title"' in html

    # CSS styles
    assert ".session-sidebar" in css
    assert ".btn-new-session" in css
    assert ".session-list" in css
    assert ".session-item" in css
    assert ".active-session-title" in css

    # JS logic
    for fn in ("loadSessions", "createSession", "selectSession", "deleteSession"):
        assert fn in js
    for export in ("PW_loadSessions", "PW_createSession", "PW_selectSession", "PW_deleteSession"):
        assert export in js
    assert "session_id" in js
    assert "/api/sessions" in js


def test_phase4_chart_ui_and_modal():
    """Phase 4: Chart image container rendering and modal zoom popup."""
    html = (FE / "index.html").read_text(encoding="utf-8")
    css = (FE / "style.css").read_text(encoding="utf-8")
    js = (FE / "app.js").read_text(encoding="utf-8")

    # HTML elements
    assert 'id="chart-modal"' in html
    assert 'id="chart-modal-backdrop"' in html
    assert 'id="chart-modal-close"' in html
    assert 'id="chart-modal-img"' in html
    assert 'id="chart-modal-caption"' in html
    assert "Vẽ biểu đồ giá FPT" in html

    # CSS styles
    assert ".chat-chart-container" in css
    assert ".chat-chart-img" in css
    assert ".chat-chart-hint" in css
    assert ".chart-modal" in css
    assert ".chart-modal-content" in css
    assert ".chart-modal-close" in css
    assert ".chart-modal-caption" in css

    # JS logic
    assert "openChartModal" in js
    assert "closeChartModal" in js
    assert "initChartModal" in js
    assert "PW_openChartModal" in js
    assert "PW_closeChartModal" in js
    assert "chat-chart-container" in js
    assert "chat-chart-img" in js
    assert "chart_path" in js


def test_phase5_market_matrix_ui():
    """Phase 5: Market Watch (10D) tab, visual matrix table, colored cells, and SVG sparkline."""
    html = (FE / "index.html").read_text(encoding="utf-8")
    css = (FE / "style.css").read_text(encoding="utf-8")
    js = (FE / "app.js").read_text(encoding="utf-8")

    # Header nav tab & view sections
    assert "Market Watch (10D)" in html
    assert 'id="tab-nav-chat"' in html
    assert 'id="tab-nav-market"' in html
    assert 'id="market-matrix-view"' in html
    assert 'id="market-matrix-table"' in html
    assert 'id="market-matrix-thead"' in html
    assert 'id="market-matrix-tbody"' in html
    assert 'id="btn-refresh-matrix"' in html
    assert 'id="market-matrix-error"' in html

    # CSS classes
    assert ".header-nav" in css
    assert ".header-nav-tab" in css
    assert ".market-matrix-view" in css
    assert ".matrix-table" in css
    assert ".matrix-cell-up" in css
    assert ".matrix-cell-down" in css
    assert ".matrix-cell-ref" in css
    assert ".sparkline-svg" in css

    # JS functions & exports
    for fn in ("generateSparklineSvg", "renderMarketMatrix", "loadMarketMatrix", "switchView", "initHeaderNav"):
        assert fn in js
    for export in ("PW_switchView", "PW_loadMarketMatrix", "PW_renderMarketMatrix", "PW_generateSparklineSvg"):
        assert export in js
    assert "/market/matrix-10d" in js
    assert "/v1/" not in js


def test_phase6_hitl_feedback_ui():
    """Phase 6: HITL answer evaluation toolbar, thumbs up/down, 1-5 stars, feedback form, and toast."""
    html = (FE / "index.html").read_text(encoding="utf-8")
    css = (FE / "style.css").read_text(encoding="utf-8")
    js = (FE / "app.js").read_text(encoding="utf-8")

    # Toast container in HTML
    assert 'id="toast-container"' in html

    # CSS classes for HITL toolbar
    assert ".hitl-feedback-container" in css
    assert ".hitl-feedback-toolbar" in css
    assert ".btn-hitl-vote" in css
    assert ".btn-hitl-up" in css
    assert ".btn-hitl-down" in css
    assert ".hitl-star-rating" in css
    assert ".hitl-star" in css
    assert ".btn-hitl-expand-text" in css
    assert ".hitl-feedback-form" in css
    assert ".hitl-feedback-input" in css
    assert ".btn-hitl-submit" in css
    assert ".hitl-feedback-status" in css
    assert ".toast-container" in css
    assert ".toast-message" in css

    # JS functions & exports
    for fn in ("showToast", "sendHitlFeedback", "createHitlFeedbackComponent"):
        assert fn in js
    for export in ("PW_sendHitlFeedback", "PW_showToast", "PW_createHitlFeedbackComponent"):
        assert export in js
    assert "/hitl/feedback" in js
    assert "/v1/" not in js


def test_phase8_hitl_reason_dropdown():
    """Phase 8: HITL feedback reason selection dropdown and reasons list."""
    css = (FE / "style.css").read_text(encoding="utf-8")
    js = (FE / "app.js").read_text(encoding="utf-8")

    assert ".hitl-reason-select" in css
    assert "hitl-reason-select" in js
    assert "Sai số liệu giá" in js
    assert "Tin tức không đúng" in js
    assert "Sai biểu đồ" in js
    assert "Thiếu ý" in js


def test_node_execution_duration_badges():
    """Phase 11: Real-time node latency/execution duration badges in live graph & timeline."""
    css = (FE / "style.css").read_text(encoding="utf-8")
    js = (FE / "app.js").read_text(encoding="utf-8")

    # CSS badges
    assert ".node-duration-badge" in css
    assert ".timeline-duration-badge" in css

    # JS parsing & rendering
    assert "duration_s" in js
    assert "duration_ms" in js
    assert "node-duration-badge" in js
    assert "timeline-duration-badge" in js


def test_phase7_streaming_sse_and_live_inspector():
    """Phase 7: Real-time SSE streaming, typing effect, and Live Inspector live updates."""
    js = (FE / "app.js").read_text(encoding="utf-8")
    css = (FE / "style.css").read_text(encoding="utf-8")

    # Streaming endpoint
    assert "/chat/stream" in js
    assert "getReader" in js
    assert "TextDecoder" in js

    # Event handling
    assert "node_start" in js
    assert "node_finish" in js
    assert "token" in js
    assert "complete" in js

    # Live Inspector updates
    assert "renderLiveGraphNodes" in js
    assert "setGraphStatus" in js
    assert "streamingMsgDiv" in js or "chat-streaming" in js

    # CSS cursor & streaming
    assert ".chat-streaming" in css
    assert "streamBlink" in css


def test_phase7_nginx_sse_buffering_disabled():
    """Phase 7: Nginx configuration disables buffering and caching for SSE."""
    nginx_conf = (FE / "nginx.conf").read_text(encoding="utf-8")
    assert "proxy_buffering off" in nginx_conf
    assert "proxy_cache off" in nginx_conf

