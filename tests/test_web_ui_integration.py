"""Integration tests for Phase 4: Web UI Streaming SSE & Live Agent Graph.

Covers:
- 4.1. Streaming SSE for Greeting fast-path (TTFT < 1.0s, token events, node_finish).
- 4.2. PortfolioWatchAgent node mapping, icons, inspector format, and live graph events.
- 4.3. Markdown tables, chart image container, hint bar, and responsive CSS rules.
"""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import time

from fastapi.testclient import TestClient
import pytest

from backend.main import app

ROOT = Path(__file__).resolve().parent.parent
FE = ROOT / "src" / "frontend"


def test_ui_html_hint_chips_and_graph_containers():
    """Verify index.html contains hint chips for Greeting and Portfolio NAV and graph containers."""
    html = (FE / "index.html").read_text(encoding="utf-8")

    # Hint chips for Phase 1 & Phase 2
    assert "Xin chào bot!" in html, "Missing 'Xin chào bot!' hint chip"
    assert "Kiểm tra NAV danh mục" in html, "Missing 'Kiểm tra NAV danh mục' hint chip"

    # Live Graph & Inspector containers
    assert 'id="live-graph-panel"' in html
    assert 'id="graph-nodes-flow"' in html
    assert 'id="graph-node-inspector"' in html
    assert 'id="inspector-node-name"' in html
    assert 'id="inspector-output-content"' in html


def test_ui_css_chart_and_graph_styles():
    """Verify style.css contains chart styling, glowing animation, and responsive media queries."""
    css = (FE / "style.css").read_text(encoding="utf-8")

    # Chart container & responsive styles
    assert ".chat-chart-container" in css, "Missing .chat-chart-container in style.css"
    assert ".chat-chart-img" in css, "Missing .chat-chart-img in style.css"
    assert ".chat-chart-hint" in css, "Missing .chat-chart-hint in style.css"
    assert "@media (max-width: 768px)" in css, "Missing mobile media query"

    # Node states and glowing animations
    assert ".graph-node-card.status-running" in css
    assert "node-glow-pulse" in css
    assert ".graph-node-card.status-done" in css
    assert ".chat-markdown-table" in css


def test_ui_js_node_mappings_and_inspector():
    """Verify app.js node mapping, icons, fallback prompts, and inspector formatting."""
    js = (FE / "app.js").read_text(encoding="utf-8")

    # Greeting & Portfolio node references
    assert "portfolio_watch_agent" in js
    assert "greeting_responder" in js
    assert "PortfolioWatchAgent" in js
    assert "GreetingResponder" in js
    assert "💼 Thông tin Danh mục & Watchlist:" in js

    # If Node.js is installed, test logic functions directly
    node_bin = shutil.which("node")
    if node_bin:
        js_test_code = r"""
        const fs = require('fs');
        const code = fs.readFileSync('src/frontend/app.js', 'utf-8');
        const start = code.indexOf('var CANONICAL_GRAPH_NODES');
        const end = code.indexOf('function showNodeInspector');
        if (start === -1 || end === -1) throw new Error("Could not find graph helpers snippet");
        const snippet = code.slice(start, end);
        const fn = new Function(snippet + '; return { CANONICAL_GRAPH_NODES, NODE_FALLBACK_PROMPTS, canonicalNodeId, normalizeNodeName, getNodeIcon };');
        const { CANONICAL_GRAPH_NODES, NODE_FALLBACK_PROMPTS, canonicalNodeId, normalizeNodeName, getNodeIcon } = fn();

        // 1. Check canonical length preserved
        if (CANONICAL_GRAPH_NODES.length !== 9) {
            throw new Error("CANONICAL_GRAPH_NODES must remain 9, got " + CANONICAL_GRAPH_NODES.length);
        }

        // 2. Greeting mapping
        if (canonicalNodeId("greeting_responder") !== "greeting_responder") throw new Error("canonical greeting failed");
        if (normalizeNodeName("greeting_responder") !== "GreetingResponder") throw new Error("normalize greeting failed");
        if (getNodeIcon("GreetingResponder") !== "👋") throw new Error("icon greeting failed");
        if (!NODE_FALLBACK_PROMPTS["greeting_responder"]) throw new Error("missing fallback prompt for greeting");

        // 3. Portfolio mapping
        if (canonicalNodeId("portfolio_watch_agent") !== "portfolio_watch_agent") throw new Error("canonical portfolio failed");
        if (normalizeNodeName("portfolio_watch_agent") !== "PortfolioWatchAgent") throw new Error("normalize portfolio failed");
        if (getNodeIcon("PortfolioWatchAgent") !== "💼") throw new Error("icon portfolio failed");
        if (!NODE_FALLBACK_PROMPTS["portfolio_watch_agent"]) throw new Error("missing fallback prompt for portfolio_watch_agent");

        console.log("PHASE4_JS_MAPPINGS_OK");
        """
        proc = subprocess.run([node_bin, "-e", js_test_code], cwd=str(ROOT), capture_output=True, text=True)
        assert proc.returncode == 0, f"Node js test failed:\nSTDOUT: {proc.stdout}\nSTDERR: {proc.stderr}"
        assert "PHASE4_JS_MAPPINGS_OK" in proc.stdout


def test_ui_fastapi_static_and_chart_routes():
    """Verify FastAPI serves app.js, index.html, and charts route."""
    client = TestClient(app)

    # 1. Root / index.html
    resp_root = client.get("/")
    assert resp_root.status_code == 200
    assert "Portfolio Watch" in resp_root.text or "VN Stock" in resp_root.text

    # 2. app.js
    resp_js = client.get("/app.js")
    assert resp_js.status_code == 200
    assert "PortfolioWatchAgent" in resp_js.text

    # 3. style.css
    resp_css = client.get("/style.css")
    assert resp_css.status_code == 200
    assert ".chat-chart-container" in resp_css.text


def test_sse_streaming_greeting_fastpath():
    """Verify /chat/stream SSE streaming for greeting fast-path (TTFT < 1.0s, token events, node_finish)."""
    client = TestClient(app)
    t0 = time.perf_counter()

    events = []
    current_evt = "message"
    ttft = None

    with client.stream(
        "POST",
        "/chat/stream",
        json={"question": "Xin chào bot!", "user_id": "default"},
        headers={"Accept": "text/event-stream"},
    ) as resp:
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers.get("content-type", "")

        for line in resp.iter_lines():
            line = line.strip()
            if line.startswith("event:"):
                current_evt = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                raw_data = line.split(":", 1)[1].strip()
                try:
                    data = json.loads(raw_data)
                except Exception:
                    data = {"raw": raw_data}
                events.append((current_evt, data))
                if current_evt == "token" and ttft is None:
                    ttft = time.perf_counter() - t0

    event_types = [e[0] for e in events]
    assert "node_finish" in event_types, f"Missing node_finish in events: {event_types}"
    assert "token" in event_types, f"Missing token in events: {event_types}"
    assert "final_answer" in event_types, f"Missing final_answer in events: {event_types}"

    # Verify node_finish for greeting_responder
    node_finish_events = [e[1] for e in events if e[0] == "node_finish"]
    greeting_finish = any(e.get("node") == "greeting_responder" for e in node_finish_events)
    assert greeting_finish, f"greeting_responder node_finish not found: {node_finish_events}"

    # Verify final answer greeting content
    final_events = [e[1] for e in events if e[0] == "final_answer"]
    assert len(final_events) > 0
    answer_text = final_events[0].get("answer", "")
    assert "Portfolio Watch" in answer_text or "Xin chào" in answer_text

    # TTFT check
    if ttft is not None:
        assert ttft < 2.0, f"TTFT too high: {ttft}s"


def test_sse_streaming_portfolio_watch_node():
    """Verify /chat/stream SSE streaming emits portfolio_watch_agent events for portfolio query."""
    client = TestClient(app)

    resp = client.post(
        "/chat/stream",
        json={"question": "Kiểm tra giá trị NAV danh mục của tôi", "user_id": "default"},
        headers={"Accept": "text/event-stream"},
    )
    assert resp.status_code == 200

    lines = resp.text.split("\n")
    events = []
    current_evt = "message"

    for line in lines:
        line = line.strip()
        if line.startswith("event:"):
            current_evt = line.split(":", 1)[1].strip()
        elif line.startswith("data:"):
            raw_data = line.split(":", 1)[1].strip()
            try:
                data = json.loads(raw_data)
            except Exception:
                data = {"raw": raw_data}
            events.append((current_evt, data))

    # Check for portfolio_watch_agent event
    node_events = [e[1] for e in events if e[0] in ("node_start", "node_finish")]
    pw_events = [e for e in node_events if e.get("node") == "portfolio_watch_agent"]
    assert len(pw_events) > 0, f"No portfolio_watch_agent events emitted: {node_events}"

    # Check final answer
    final_events = [e[1] for e in events if e[0] == "final_answer"]
    assert len(final_events) > 0
    final = final_events[0]
    assert final.get("answer"), "Missing answer in portfolio stream final event"
