"""System, Docker, Frontend, Environment & Documentation tests (tests/test_system.py).

Comprehensive tests for:
1. Docker compose configuration: microservices (backend & frontend), volume, healthcheck, no hardcoded secrets.
2. Dockerfile & Nginx configuration for backend and frontend.
3. Environment variables in .env.example (Memory, Langfuse, Monitoring, Qdrant).
4. Product FastAPI app serving /health and Web UI statically at /.
5. Frontend Static SPA layout: Claude-style column, timeline, watchlist, approvals, inspector.
6. Frontend single-origin API wiring: calls backend endpoints directly (/chat, /scan, /market).
7. Documentation consistency: README quick start, docker compose commands, and local development.
"""

from __future__ import annotations

import re
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from backend.main import app as product_app

ROOT = Path(__file__).resolve().parents[1]
FE = ROOT / "src" / "frontend"
if not FE.is_dir():
    FE = ROOT / "frontend"
if not FE.is_dir():
    FE = ROOT / "src" / "portfolio_watch" / "frontend"


# ==============================================================================
# 1. Docker Compose & Dockerfile Configuration Tests
# ==============================================================================

def test_compose_two_services_backend_and_frontend_and_volume():
    """Kiểm tra docker-compose.yml có đúng 2 services (backend, frontend), volume pw_data và healthcheck."""
    text = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert "\n  backend:" in text
    assert "\n  frontend:" in text
    assert "qdrant" in text
    assert "profiles:" in text
    assert "pw_data:/app/data" in text
    assert "SQLITE_PATH: /app/data/portfolio_watch.db" in text
    assert "BACKEND_SQLITE_PATH: /app/data/backend_store.db" in text
    assert ("backend.main" in text) or ("backend.backend.main" in text)
    assert "healthcheck:" in text
    assert "AI_TRANSPORT" in text
    assert "LANGFUSE_HOST" in text
    assert "sk-" not in text.lower()


def test_dockerfile_and_frontend_dockerfile():
    """Kiểm tra backend Dockerfile và frontend Dockerfile / nginx.conf."""
    df_path = ROOT / "src" / "backend" / "Dockerfile" if (ROOT / "src" / "backend" / "Dockerfile").is_file() else ROOT / "Dockerfile"
    df = df_path.read_text(encoding="utf-8")
    assert ("backend.main:app" in df) or ("backend.backend.main:app" in df)
    assert ("USER appuser" in df) or ("gosu appuser" in df)
    assert "HEALTHCHECK" in df

    fe_df_path = ROOT / "src" / "frontend" / "Dockerfile" if (ROOT / "src" / "frontend" / "Dockerfile").is_file() else ROOT / "frontend" / "Dockerfile"
    fe_df = fe_df_path.read_text(encoding="utf-8")
    assert "nginx" in fe_df
    assert (ROOT / "src" / "frontend" / "nginx.conf").is_file() or (ROOT / "frontend" / "nginx.conf").is_file()


def test_phase10_nginx_sse_buffering_disabled():
    """nginx.conf tắt proxy_buffering cho SSE (/api/, /chat)."""
    nginx = (ROOT / "src" / "frontend" / "nginx.conf").read_text(encoding="utf-8")
    assert "location /api/" in nginx
    assert "location /chat" in nginx
    for block in ("/api/", "/chat"):
        start = nginx.index(f"location {block}")
        chunk = nginx[start : start + 400]
        assert "proxy_buffering off" in chunk
        assert "proxy_cache off" in chunk


def test_llm_semaphore_limits_concurrency(monkeypatch):
    """LLM_SEMAPHORE giới hạn số call đồng thời."""
    import threading
    import time

    from backend.infra.llm.semaphore import llm_semaphore_slot, reset_llm_semaphore_for_tests

    monkeypatch.setenv("LLM_SEMAPHORE", "2")
    reset_llm_semaphore_for_tests()
    active = 0
    peak = 0
    lock = threading.Lock()

    def worker() -> None:
        nonlocal active, peak
        with llm_semaphore_slot():
            with lock:
                active += 1
                peak = max(peak, active)
            time.sleep(0.05)
            with lock:
                active -= 1

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert peak <= 2


def test_ai_client_retries_429(monkeypatch):
    """ai_client retry 429 với backoff."""
    import urllib.error
    import urllib.request

    from backend import ai_client

    calls = {"n": 0}

    def fake_urlopen(req, timeout=None):
        calls["n"] += 1
        if calls["n"] < 3:
            raise urllib.error.HTTPError(
                req.full_url, 429, "Too Many Requests", hdrs=None, fp=None
            )
        return type("R", (), {"read": lambda self: b'{"ok": true}', "__enter__": lambda s: s, "__exit__": lambda *a: None})()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setenv("AI_TRANSPORT", "http")
    monkeypatch.setenv("AI_HTTP_MAX_RETRIES", "3")
    monkeypatch.setattr(ai_client, "_retry_delay", lambda _attempt: 0.0)

    out = ai_client._post_json("/v1/chat", {"question": "FPT"})
    assert out["ok"] is True
    assert calls["n"] == 3


def test_inprocess_ai_transport_default(monkeypatch):
    """Mặc định product: AI in-process, không bắt buộc service ngoài."""
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    env_ex = (ROOT / ".env.example").read_text(encoding="utf-8")
    assert 'AI_TRANSPORT: "inprocess"' in compose
    assert "AI_TRANSPORT=inprocess" in env_ex
    assert "\n  ai:" not in compose

    from backend.ai_client import _use_http

    monkeypatch.delenv("AI_TRANSPORT", raising=False)
    assert _use_http() is False
    monkeypatch.setenv("AI_TRANSPORT", "http")
    assert _use_http() is True


# ==============================================================================
# 2. Environment Variables (.env.example) Tests
# ==============================================================================

def test_env_example_has_required_vars_and_no_secrets():
    """Kiểm tra .env.example có đầy đủ các biến cấu hình và không chứa secret thật."""
    env_example_path = ROOT / ".env.example"
    assert env_example_path.exists()
    content = env_example_path.read_text(encoding="utf-8")

    expected_vars = [
        "MEMORY_SHORT_TERM_WINDOW",
        "MEMORY_SHORT_TERM_TTL_MINUTES",
        "QDRANT_URL",
        "QDRANT_API_KEY",
        "QDRANT_COLLECTION",
        "EMBEDDING_MODEL",
        "EMBEDDING_DIM",
        "MONITORING_ENABLED",
        "LANGFUSE_PUBLIC_KEY",
        "LANGFUSE_SECRET_KEY",
        "LANGFUSE_HOST",
        "APP_HOST_PORT",
    ]
    for var in expected_vars:
        assert f"{var}=" in content, f"Missing {var} in .env.example"

    # Kiểm tra không lộ OpenAI API Key thật
    secrets = re.findall(r"sk-[A-Za-z0-9_\-]+", content)
    for secret in secrets:
        assert "xxxxx" in secret or secret in ["sk-lf", "sk-proj-xxxxx", "sk-proj-"], f"Found potential secret: {secret}"


# ==============================================================================
# 3. Product App Health & Static Serving Tests
# ==============================================================================

def test_product_app_serves_health_and_ui():
    """Kiểm tra backend FastAPI phục vụ /health và UI tĩnh tại root /."""
    assert (FE / "index.html").is_file()
    client = TestClient(product_app)
    assert client.get("/health").status_code == 200
    assert client.get("/").status_code == 200


# ==============================================================================
# 4. Frontend Static Files & Layout Tests
# ==============================================================================

def test_frontend_files_and_layout():
    """Kiểm tra các tệp tĩnh Frontend và cấu trúc giao diện Claude-style."""
    for name in ("index.html", "app.js", "style.css", "config.js"):
        assert (FE / name).is_file(), f"Missing frontend file: {name}"

    html = (FE / "index.html").read_text(encoding="utf-8")
    css = (FE / "style.css").read_text(encoding="utf-8")

    # Bố cục 2 cột Claude-style
    assert "chat-column" in html
    assert "chat-messages" in html
    assert "composer-container" in html
    assert "chat-form" in html
    assert "chat-input" in html
    assert "chat-send" in html

    # Tab phụ: timeline, watchlist, approvals
    assert "secondary-column" in html
    assert "secondary-tabs" in html
    for sid in ("chat", "timeline", "watchlist", "approvals"):
        assert f'id="{sid}"' in html

    # CSS class
    assert ".chat-column" in css
    assert ".composer-container" in css


def test_frontend_single_origin_api_wiring():
    """Kiểm tra Frontend gọi trực tiếp backend endpoints, không gọi riêng lẻ service khác."""
    js = (FE / "app.js").read_text(encoding="utf-8")
    cfg = (FE / "config.js").read_text(encoding="utf-8")

    assert "BACKEND_BASE_URL" in cfg
    for ep in ("/chat", "/scan", "/market", "/watchlist", "/approvals"):
        assert ep in js
    assert "8001" not in js
    assert "MOCK_STEPS" not in js


def test_phase2_frontend_static_serving_and_mime_types():
    """Phase 2.1: Kiểm tra FastAPI mount tĩnh Frontend và trả về đúng MIME types."""
    from fastapi.testclient import TestClient
    from backend.main import app

    client = TestClient(app)

    # 1. Root / trả về index.html (200 OK)
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")
    assert "Portfolio Watch" in resp.text

    # 2. Các file tĩnh cốt lõi
    resp_css = client.get("/style.css")
    assert resp_css.status_code == 200
    assert "text/css" in resp_css.headers.get("content-type", "")

    resp_js = client.get("/app.js")
    assert resp_js.status_code == 200
    assert "javascript" in resp_js.headers.get("content-type", "")

    resp_cfg = client.get("/config.js")
    assert resp_cfg.status_code == 200
    assert "javascript" in resp_cfg.headers.get("content-type", "")

    # 3. Mount charts và static/charts endpoint
    assert any(getattr(route, "path", None) == "/charts" for route in app.routes)
    assert any(getattr(route, "path", None) == "/static/charts" for route in app.routes)


def test_phase2_user_switcher_wiring_and_tenant_isolation():
    """Phase 2.2: Kiểm tra User Switcher UI và tính cô lập dữ liệu giữa user_a và user_b."""
    from fastapi.testclient import TestClient
    from backend.main import app

    html = (FE / "index.html").read_text(encoding="utf-8")
    js = (FE / "app.js").read_text(encoding="utf-8")

    # 1. UI element và các options
    assert 'id="user-switcher-select"' in html
    assert 'value="user_a"' in html
    assert 'value="user_b"' in html
    assert 'value="default"' in html

    # 2. JS persistence và dynamic header wiring
    assert "PW_CURRENT_USER_ID" in js
    assert "getCurrentUserId" in js
    assert "setCurrentUserId" in js
    assert '"X-User-ID": getCurrentUserId()' in js

    # 3. API Tenant Isolation check (AC-7)
    client = TestClient(app)
    user_a = "tenant_test_user_a"
    user_b = "tenant_test_user_b"

    # Thêm mã vào watchlist của user_a
    resp_add = client.post(
        "/watchlist",
        json={"symbol": "FPT", "threshold_pct": 3.0, "user_id": user_a},
        headers={"X-User-ID": user_a},
    )
    assert resp_add.status_code in (200, 201)

    # Lấy watchlist của user_a -> có FPT
    resp_a = client.get(f"/watchlist?user_id={user_a}", headers={"X-User-ID": user_a})
    assert resp_a.status_code == 200
    symbols_a = [item["symbol"] for item in resp_a.json().get("items", [])]
    assert "FPT" in symbols_a

    # Lấy watchlist của user_b -> không bị lẫn FPT của user_a
    resp_b = client.get(f"/watchlist?user_id={user_b}", headers={"X-User-ID": user_b})
    assert resp_b.status_code == 200
    symbols_b = [item["symbol"] for item in resp_b.json().get("items", [])]
    assert "FPT" not in symbols_b


def test_phase2_chat_markdown_rendering():
    """Phase 2.3: Kiểm tra Khung Chat và Trình Kết Xuất Markdown (bảng, in đậm, code, chart image, XSS)."""
    import subprocess
    import shutil
    from fastapi.testclient import TestClient
    from backend.main import app

    html = (FE / "index.html").read_text(encoding="utf-8")
    js = (FE / "app.js").read_text(encoding="utf-8")
    css = (FE / "style.css").read_text(encoding="utf-8")

    # 1. Khung chat container và input elements trong index.html
    assert 'id="chat-messages"' in html
    assert 'id="chat-input"' in html
    assert 'id="chat-send"' in html

    # 2. CSS định kiểu đầy đủ cho Markdown Body, Bảng, Code block, Chart Container
    assert ".msg-text.markdown-body" in css
    assert ".chat-markdown-table" in css
    assert ".chat-code-block" in css
    assert ".chat-chart-container" in css
    assert ".chat-blockquote" in css

    # 3. JS Parser logic trong app.js
    assert "function renderMarkdown" in js
    assert "PW_renderMarkdown" in js
    assert "chat-markdown-table" in js
    assert "chat-chart-container" in js

    # 4. Kiểm thử thực thi logic JavaScript qua Node.js (nếu có sẵn trên hệ thống)
    node_bin = shutil.which("node")
    if node_bin:
        js_test_code = r"""
        const fs = require('fs');
        const code = fs.readFileSync('src/frontend/app.js', 'utf-8');
        const start = code.indexOf('function escapeHtml');
        const end = code.indexOf('function appendChat');
        if (start === -1 || end === -1) throw new Error("Could not find escapeHtml or appendChat");
        const snippet = code.slice(start, end);
        const fn = new Function(snippet + '; return { escapeHtml, renderMarkdown };');
        const { renderMarkdown, escapeHtml } = fn();

        const sampleMarkdown = `
### Phân tích FPT
Cổ phiếu **FPT** đang trong xu hướng tăng mạnh với giá *125.4*.

| Mã | Giá (VND) | Khuyến nghị |
|---|---|---|
| FPT | 125,400 | Tích cực |
| HPG | 28,500 | Theo dõi |

![Biểu đồ FPT](/static/charts/chart_demo123.png)

> Khuyến cáo: Thông tin mang tính tham khảo kỹ thuật.

\`\`\`python
print("RSI: 68")
\`\`\`

- Kháng cự: 130
- Hỗ trợ: 120
<script>alert("hack")</script>
`;

        const htmlOut = renderMarkdown(sampleMarkdown);
        if (!htmlOut.includes("<strong>FPT</strong>")) throw new Error("Bold failed");
        if (!htmlOut.includes("<em>125.4</em>")) throw new Error("Italic failed");
        if (!htmlOut.includes('<table class="chat-markdown-table">')) throw new Error("Table failed");
        if (!htmlOut.includes("<th>Mã</th>")) throw new Error("Table header failed");
        if (!htmlOut.includes("<td>125,400</td>")) throw new Error("Table cell failed");
        if (!htmlOut.includes("/static/charts/chart_demo123.png")) throw new Error("Chart path failed");
        if (!htmlOut.includes("chat-chart-container")) throw new Error("Chart container failed");
        if (!htmlOut.includes('<blockquote class="chat-blockquote">')) throw new Error("Blockquote failed");
        if (!htmlOut.includes('<pre class="chat-code-block">')) throw new Error("Code block failed");
        if (htmlOut.includes("<script>")) throw new Error("XSS vulnerability detected");
        if (!htmlOut.includes("&lt;script&gt;")) throw new Error("XSS sanitization failed");
        console.log("MARKDOWN_TEST_OK");
        """
        proc = subprocess.run([node_bin, "-e", js_test_code], cwd=str(ROOT), capture_output=True, text=True)
        assert proc.returncode == 0, f"Node markdown test failed:\nSTDOUT: {proc.stdout}\nSTDERR: {proc.stderr}"
        assert "MARKDOWN_TEST_OK" in proc.stdout

    # 5. Kiểm tra qua FastAPI TestClient (MIME và nội dung)
    client = TestClient(app)
    resp = client.get("/app.js")
    assert resp.status_code == 200
    assert "renderMarkdown" in resp.text


def test_phase2_live_agent_graph_and_node_inspector():
    """Phase 2.4: Kiểm tra Đồ thị mạng lưới Live Agent Graph (9 nodes canonical, highlight, inspector, prompts)."""
    import subprocess
    import shutil
    from fastapi.testclient import TestClient
    from backend.main import app

    html = (FE / "index.html").read_text(encoding="utf-8")
    js = (FE / "app.js").read_text(encoding="utf-8")
    css = (FE / "style.css").read_text(encoding="utf-8")

    # 1. Khung hiển thị đồ thị và inspector trong index.html
    assert 'id="live-graph-panel"' in html
    assert 'id="graph-nodes-flow"' in html
    assert 'id="graph-node-inspector"' in html
    assert 'id="inspector-node-name"' in html
    assert 'id="inspector-node-badge"' in html
    assert 'id="inspector-static-content"' in html
    assert 'id="inspector-input-content"' in html
    assert 'id="inspector-output-content"' in html

    # 2. CSS định kiểu trạng thái node và hiệu ứng phát sáng
    assert ".graph-node-card.status-idle" in css
    assert ".graph-node-card.status-running" in css
    assert ".graph-node-card.status-done" in css
    assert "node-glow-pulse" in css
    assert ".graph-node-inspector" in css

    # 3. Mã nguồn app.js khai báo đủ 9 node canonical
    canonical_names = [
        "Guardrail", "Rewrite", "Supervisor", "PriceAgent",
        "NewsAgent", "IndicatorEngine", "ChartAgent", "EvalAgent", "AnswerComposer"
    ]
    for name in canonical_names:
        assert f'name: "{name}"' in js or f'"{name}"' in js, f"Missing canonical node {name} in app.js"

    assert "PW_CANONICAL_GRAPH_NODES" in js
    assert "PW_NODE_FALLBACK_PROMPTS" in js
    assert "normalizeNodeName" in js
    assert "showNodeInspector" in js

    # 4. Kiểm thử logic thực thi qua Node.js (nếu có sẵn)
    node_bin = shutil.which("node")
    if node_bin:
        js_test_code = r"""
        const fs = require('fs');
        const code = fs.readFileSync('src/frontend/app.js', 'utf-8');
        const start = code.indexOf('var CANONICAL_GRAPH_NODES');
        const end = code.indexOf('function showNodeInspector');
        if (start === -1 || end === -1) throw new Error("Could not find graph helpers snippet");
        const snippet = code.slice(start, end);
        const fn = new Function(snippet + '; return { CANONICAL_GRAPH_NODES, NODE_FALLBACK_PROMPTS, canonicalNodeId, normalizeNodeName, getNodeIcon, getCanonicalInitialNodes };');
        const { CANONICAL_GRAPH_NODES, NODE_FALLBACK_PROMPTS, canonicalNodeId, normalizeNodeName, getNodeIcon, getCanonicalInitialNodes } = fn();

        // 4.1 Đủ 9 node canonical
        if (!Array.isArray(CANONICAL_GRAPH_NODES) || CANONICAL_GRAPH_NODES.length !== 9) {
            throw new Error("CANONICAL_GRAPH_NODES must have exactly 9 nodes, got: " + (CANONICAL_GRAPH_NODES ? CANONICAL_GRAPH_NODES.length : 0));
        }

        const requiredNames = ["Guardrail", "Rewrite", "Supervisor", "PriceAgent", "NewsAgent", "IndicatorEngine", "ChartAgent", "EvalAgent", "AnswerComposer"];
        requiredNames.forEach(name => {
            const found = CANONICAL_GRAPH_NODES.find(n => n.name === name);
            if (!found) throw new Error("Missing canonical node: " + name);
        });

        // 4.2 Mọi node đều có System Prompt / Fallback info
        CANONICAL_GRAPH_NODES.forEach(n => {
            const prompt = NODE_FALLBACK_PROMPTS[n.id] || NODE_FALLBACK_PROMPTS[n.name.toLowerCase()];
            if (!prompt) throw new Error("Missing system prompt for canonical node: " + n.name);
        });

        // 4.3 Chuẩn hóa tên node từ backend event
        if (normalizeNodeName("pre_rewrite_guardrail") !== "Guardrail") throw new Error("normalize guardrail failed");
        if (normalizeNodeName("rewrite_question") !== "Rewrite") throw new Error("normalize rewrite failed");
        if (normalizeNodeName("price_agent") !== "PriceAgent") throw new Error("normalize price failed");
        if (normalizeNodeName("indicator_engine") !== "IndicatorEngine") throw new Error("normalize indicator failed");
        if (normalizeNodeName("chart_agent") !== "ChartAgent") throw new Error("normalize chart failed");
        if (normalizeNodeName("eval_agent") !== "EvalAgent") throw new Error("normalize eval failed");
        if (normalizeNodeName("answer_composer") !== "AnswerComposer") throw new Error("normalize composer failed");

        // 4.4 Icon hợp lệ cho các node
        if (getNodeIcon("IndicatorEngine") !== "📐") throw new Error("Indicator icon failed");
        if (getNodeIcon("ChartAgent") !== "📊") throw new Error("Chart icon failed");
        if (getNodeIcon("Guardrail") !== "🛡️") throw new Error("Guardrail icon failed");

        // 4.5 Trạng thái idle khởi tạo
        const initialNodes = getCanonicalInitialNodes();
        if (initialNodes.length !== 9 || !initialNodes.every(n => n.status === "idle")) {
            throw new Error("Initial canonical nodes must all be status idle");
        }

        console.log("LIVE_GRAPH_TEST_OK");
        """
        proc = subprocess.run([node_bin, "-e", js_test_code], cwd=str(ROOT), capture_output=True, text=True)
        assert proc.returncode == 0, f"Node live graph test failed:\nSTDOUT: {proc.stdout}\nSTDERR: {proc.stderr}"
        assert "LIVE_GRAPH_TEST_OK" in proc.stdout

    # 5. Kiểm tra qua FastAPI TestClient
    client = TestClient(app)
    resp = client.get("/app.js")
    assert resp.status_code == 200
    assert "CANONICAL_GRAPH_NODES" in resp.text





def test_phase2_portfolio_pnl_table_and_summary_cards():
    """Phase 2.5: Kiểm tra Bảng hiển thị Danh mục & P&L, 3 thẻ tóm tắt NAV/PnL và API CRUD."""
    from fastapi.testclient import TestClient
    from backend.main import app

    html = (FE / "index.html").read_text(encoding="utf-8")
    css = (FE / "style.css").read_text(encoding="utf-8")
    js = (FE / "app.js").read_text(encoding="utf-8")

    # 1. Kiểm tra cấu trúc HTML
    assert 'id="portfolio"' in html
    assert 'id="pnl-total-nav"' in html, "Thiếu thẻ hiển thị Tổng NAV"
    assert 'id="pnl-total-pnl"' in html, "Thiếu thẻ hiển thị Tổng Lãi/Lỗ"
    assert 'id="pnl-total-pct"' in html, "Thiếu thẻ hiển thị Tỷ suất sinh lời %"
    assert 'id="portfolio-add-form"' in html, "Thiếu form thêm cổ phiếu vào danh mục"
    assert 'id="portfolio-symbol"' in html
    assert 'id="portfolio-quantity"' in html
    assert 'id="portfolio-price"' in html
    assert 'id="portfolio-add-btn"' in html
    assert 'id="btn-refresh-portfolio"' in html
    assert 'id="portfolio-body"' in html

    # Kiểm tra đủ 7 cột bảng P&L
    for col_header in ("Mã", "SL", "Giá vốn", "Thị giá", "Lãi/Lỗ", "% Lời", "Xóa"):
        assert col_header in html, f"Thiếu cột {col_header} trong bảng danh mục P&L"

    # 2. Kiểm tra CSS định dạng
    assert ".portfolio-summary-cards" in css
    assert ".pnl-card" in css
    assert ".pnl-card-val" in css
    assert ".pnl-up" in css
    assert ".pnl-down" in css
    assert ".pnl-ref" in css
    assert ".portfolio-table" in css
    assert ".btn-delete-holding" in css

    # 3. Kiểm tra logic JS
    assert "loadPortfolio" in js
    assert "doAddHolding" in js
    assert "doDeleteHolding" in js
    assert "portfolio-body" in js
    assert "escapeHtml" in js

    # 4. Kiểm tra Backend API endpoints & aliases (AC-7)
    client = TestClient(app)
    user_alpha = "pnl_test_user_alpha"
    user_beta = "pnl_test_user_beta"

    # 4.1 Người dùng mới: danh mục trống
    resp_empty = client.get("/api/v1/portfolio/summary", headers={"X-User-ID": user_alpha})
    assert resp_empty.status_code == 200
    data_empty = resp_empty.json()
    assert data_empty["total_nav"] == 0.0
    assert data_empty["total_unrealized_pnl"] == 0.0
    assert data_empty["items"] == []

    # 4.2 Thêm vị thế qua endpoint /api/v1/portfolio/holdings
    resp_add = client.post(
        "/api/v1/portfolio/holdings",
        headers={"X-User-ID": user_alpha},
        json={"symbol": "FPT", "quantity": 100, "avg_buy_price": 100.0},
    )
    assert resp_add.status_code == 201
    holding_id = resp_add.json()["id"]

    # 4.3 Kiểm tra danh mục qua /api/portfolio và /api/v1/portfolio
    resp_summary = client.get("/api/portfolio", headers={"X-User-ID": user_alpha})
    assert resp_summary.status_code == 200
    summary = resp_summary.json()
    assert summary["count"] == 1
    assert summary["items"][0]["symbol"] == "FPT"
    assert summary["items"][0]["quantity"] == 100
    assert summary["total_nav"] > 0

    # 4.4 Kiểm tra endpoint /api/v1/portfolio/holdings trả về danh sách items
    resp_holdings = client.get("/api/v1/portfolio/holdings", headers={"X-User-ID": user_alpha})
    assert resp_holdings.status_code == 200
    holdings_list = resp_holdings.json()
    assert len(holdings_list) == 1
    assert holdings_list[0]["symbol"] == "FPT"

    # 4.5 Cô lập dữ liệu: user_beta không bị lẫn dữ liệu của user_alpha
    resp_beta = client.get("/api/v1/portfolio", headers={"X-User-ID": user_beta})
    assert resp_beta.status_code == 200
    assert resp_beta.json()["count"] == 0

    # 4.6 Xóa vị thế qua /api/v1/portfolio/holdings/{id}
    resp_del = client.delete(f"/api/v1/portfolio/holdings/{holding_id}", headers={"X-User-ID": user_alpha})
    assert resp_del.status_code == 200

    # Kiểm tra lại danh mục của user_alpha sau khi xóa
    resp_after = client.get("/api/portfolio", headers={"X-User-ID": user_alpha})
    assert resp_after.status_code == 200
    assert resp_after.json()["count"] == 0


# ==============================================================================
# 5. Documentation & README Consistency Tests
# ==============================================================================

def test_readme_docker_product_and_local():
    """Kiểm tra README.md có hướng dẫn Docker Compose và chạy Local đầy đủ."""
    content = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "docker compose up --build" in content
    assert "uvicorn backend.main" in content or "uvicorn backend.backend.main" in content or "python -m backend.main" in content

# ==============================================================================
# 6. Deploy & Smoke Testing (Phase 11)
# ==============================================================================

def test_smoke_module_imports():
    """Kiểm tra module smoke.py tồn tại và có thể parse được."""
    smoke_py = ROOT / "deploy" / "smoke.py"
    assert smoke_py.exists(), "Missing deploy/smoke.py for Phase 11"
    
    # Just read and compile to check syntax
    source = smoke_py.read_text(encoding="utf-8")
    compile(source, filename="smoke.py", mode="exec")

def test_secrets_module_imports():
    """Kiểm tra backend/shared/secrets.py tồn tại."""
    secrets_py = ROOT / "src" / "backend" / "shared" / "secrets.py"
    assert secrets_py.exists(), "Missing src/backend/shared/secrets.py for Phase 11"

    from backend.shared.secrets import get_secret

    assert get_secret("NONEXISTENT_KEY_XYZ") is None


def test_smoke_answer_validation():
    """Smoke helper chấp nhận câu trả FPT hoặc từ chối hợp lý."""
    import sys

    sys.path.insert(0, str(ROOT / "deploy"))
    from smoke import _answer_acceptable  # type: ignore

    assert _answer_acceptable("FPT hôm nay tăng 1.2% so với phiên trước.")
    assert _answer_acceptable("Câu hỏi ngoài phạm vi tra cứu chứng khoán.")
    assert not _answer_acceptable("")


def test_smoke_health_with_mock(monkeypatch):
    """run_smoke health pass với mock HTTP."""
    import io
    import json
    import sys
    import urllib.request

    sys.path.insert(0, str(ROOT / "deploy"))
    from smoke import run_smoke  # type: ignore

    class _Resp:
        def __init__(self, code: int, body: bytes):
            self._code = code
            self._body = body

        def getcode(self) -> int:
            return self._code

        def read(self) -> bytes:
            return self._body

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def fake_urlopen(req, timeout=30):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        if url.endswith("/health"):
            return _Resp(200, json.dumps({"status": "ok", "service": "backend"}).encode())
        if url.endswith("/chat"):
            payload = json.dumps({"answer": "FPT hôm nay tăng nhẹ.", "question": "FPT?"}).encode()
            return _Resp(200, payload)
        raise AssertionError(f"unexpected url {url}")

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    assert run_smoke("http://localhost:8000", check_stream_flag=False) == 0


def test_phase4_frontend_sse_and_live_graph_integration():
    """Phase 4.1: Kiểm tra hợp đồng tích hợp Web UI SSE và Live Graph lighting trong app.js và style.css."""
    js_text = (FE / "app.js").read_text(encoding="utf-8")
    css_text = (FE / "style.css").read_text(encoding="utf-8")

    # 1. Kiểm tra kết nối SSE tới POST /chat
    assert 'apiUrl("/chat")' in js_text
    assert '"text/event-stream"' in js_text

    # 2. Kiểm tra xử lý đủ 5 sự kiện SSE
    assert 'eventName === "node_start"' in js_text
    assert 'eventName === "node_end"' in js_text
    assert 'eventName === "token"' in js_text
    assert 'eventName === "chart_url"' in js_text
    assert 'eventName === "final_answer"' in js_text

    # 3. Kiểm tra hàm đồng bộ trạng thái Live Graph với Canonical Nodes
    assert "mergeWithCanonicalNodes" in js_text
    assert "renderLiveGraphNodes(mergeWithCanonicalNodes" in js_text

    # 4. Kiểm tra CSS hiệu ứng sáng đèn của node (Live Glow Pulse)
    assert ".graph-node-card.status-running" in css_text
    assert "node-glow-pulse" in css_text
    assert "@keyframes node-glow-pulse" in css_text
    assert ".graph-node-card.status-done" in css_text


def test_phase4_portfolio_api_integration():
    """Phase 4.2: Kiểm tra tích hợp Portfolio API (/api/v1/portfolio/holdings & /api/v1/portfolio/summary).
    
    Xác nhận:
    1. Web UI app.js chứa logic gọi GET /api/v1/portfolio/summary và GET /api/v1/portfolio/holdings.
    2. Hỗ trợ thêm vị thế qua POST /api/v1/portfolio/holdings và xóa vị thế qua DELETE /api/v1/portfolio/holdings/{id}.
    3. Giá trị NAV và P&L được cập nhật tức thì và cô lập hoàn toàn giữa các user.
    """
    from fastapi.testclient import TestClient
    from backend.main import app

    js_text = (FE / "app.js").read_text(encoding="utf-8")

    # 1. Kiểm tra mã nguồn app.js gọi đúng các endpoint Phase 4.2
    assert 'api("GET", "/api/v1/portfolio/summary")' in js_text
    assert 'api("GET", "/api/v1/portfolio/holdings")' in js_text
    assert 'api("POST", "/api/v1/portfolio/holdings"' in js_text
    assert 'api("DELETE", "/api/v1/portfolio/holdings/"' in js_text
    assert "pnl-total-nav" in js_text
    assert "pnl-total-pnl" in js_text
    assert "pnl-total-pct" in js_text

    # 2. Kiểm tra chuỗi tương tác API thực tế
    from backend.api.deps import get_app_deps
    from backend.domain.ports import PriceBar, PriceQuote, PriceSourcePort

    class MockPricing(PriceSourcePort):
        def fetch_latest_close(self, symbol: str) -> PriceQuote:
            sym = symbol.upper()
            if sym == "FPT":
                return PriceQuote(symbol="FPT", latest_close=120.0, prev_close=118.0)
            if sym == "HPG":
                return PriceQuote(symbol="HPG", latest_close=27.0, prev_close=27.0)
            return PriceQuote(symbol=sym, latest_close=50.0, prev_close=50.0)

        def fetch_history(self, symbol: str, lookback_days: int = 14) -> list[PriceBar]:
            return []

    deps = get_app_deps()
    old_source = deps.price_source
    deps.price_source = MockPricing()

    try:
        import uuid
        uid = uuid.uuid4().hex[:8]
        user_test = f"phase4_pnl_investor_{uid}"
        user_other = f"phase4_pnl_isolated_{uid}"
        client = TestClient(app)

        # 2.1 Trạng thái ban đầu: danh mục trống
        init_res = client.get("/api/v1/portfolio/summary", headers={"X-User-ID": user_test})
        assert init_res.status_code == 200
        init_data = init_res.json()
        assert init_data["count"] == 0
        assert init_data["total_nav"] == 0.0
        assert init_data["total_unrealized_pnl"] == 0.0
        assert init_data["items"] == []

        # 2.2 Thêm cổ phiếu FPT (1,000 cp @ giá vốn 100k)
        add_fpt = client.post(
            "/api/v1/portfolio/holdings",
            headers={"X-User-ID": user_test},
            json={"symbol": "FPT", "quantity": 1000, "avg_buy_price": 100.0},
        )
        assert add_fpt.status_code == 201
        fpt_holding = add_fpt.json()
        fpt_id = fpt_holding["id"]
        assert fpt_holding["symbol"] == "FPT"
        assert fpt_holding["quantity"] == 1000

        # 2.3 Thêm cổ phiếu HPG (2,000 cp @ giá vốn 30k)
        add_hpg = client.post(
            "/api/v1/portfolio/holdings",
            headers={"X-User-ID": user_test},
            json={"symbol": "HPG", "quantity": 2000, "avg_buy_price": 30.0},
        )
        assert add_hpg.status_code == 201
        hpg_holding = add_hpg.json()
        hpg_id = hpg_holding["id"]
        assert hpg_holding["symbol"] == "HPG"
        assert hpg_holding["quantity"] == 2000

        # 2.4 Kiểm tra nạp bảng P&L qua GET /api/v1/portfolio/summary
        summary_res = client.get("/api/v1/portfolio/summary", headers={"X-User-ID": user_test})
        assert summary_res.status_code == 200
        summary = summary_res.json()
        assert summary["count"] == 2
        assert summary["total_cost"] == 160_000_000.0
        # Giá mock: FPT = 120.0 (120k) -> 120tr, HPG = 27.0 (27k) -> 54tr => Total NAV = 174tr
        assert summary["total_nav"] == 174_000_000.0
        assert summary["total_unrealized_pnl"] == 14_000_000.0
        assert summary["total_pnl_pct"] == 8.75

        # 2.5 Kiểm tra nạp danh sách holdings qua GET /api/v1/portfolio/holdings
        holdings_res = client.get("/api/v1/portfolio/holdings", headers={"X-User-ID": user_test})
        assert holdings_res.status_code == 200
        holdings_list = holdings_res.json()
        assert len(holdings_list) == 2
        fpt_item = next(i for i in holdings_list if i["symbol"] == "FPT")
        assert fpt_item["quantity"] == 1000
        assert fpt_item["unrealized_pnl"] == 20_000_000.0
        assert fpt_item["pnl_pct"] == 20.0

        # 2.6 Kiểm tra cô lập dữ liệu với user khác (Multi-tenant)
        other_res = client.get("/api/v1/portfolio/summary", headers={"X-User-ID": user_other})
        assert other_res.status_code == 200
        assert other_res.json()["count"] == 0
        assert other_res.json()["items"] == []

        # 2.7 Xóa vị thế FPT và xác nhận NAV cập nhật tức thì
        del_res = client.delete(f"/api/v1/portfolio/holdings/{fpt_id}", headers={"X-User-ID": user_test})
        assert del_res.status_code == 200
        assert del_res.json()["ok"] is True

        # 2.8 Kiểm tra lại sau khi xóa: chỉ còn HPG, NAV tức thì giảm còn 54,000,000 VND
        after_del_res = client.get("/api/v1/portfolio/summary", headers={"X-User-ID": user_test})
        assert after_del_res.status_code == 200
        after_summary = after_del_res.json()
        assert after_summary["count"] == 1
        assert after_summary["items"][0]["symbol"] == "HPG"
        assert after_summary["total_nav"] == 54_000_000.0
        assert after_summary["total_cost"] == 60_000_000.0
        assert after_summary["total_unrealized_pnl"] == -6_000_000.0
        assert after_summary["total_pnl_pct"] == -10.0
    finally:
        deps.price_source = old_source


def test_phase4_watchlist_api_integration():
    """Phase 4.3: Kiểm tra tích hợp Watchlist API (/api/v1/watchlist & alert_threshold_pct).
    
    Xác nhận:
    1. Web UI app.js chứa logic gọi GET /api/v1/watchlist và hỗ trợ trường alert_threshold_pct.
    2. Hỗ trợ đầy đủ CRUD: GET, POST thêm mã, PATCH sửa ngưỡng cảnh báo, DELETE xóa mã.
    3. Cô lập đa người dùng (Multi-tenant) qua header X-User-ID.
    """
    import uuid
    from fastapi.testclient import TestClient
    from backend.main import app

    js_text = (FE / "app.js").read_text(encoding="utf-8")

    # 1. Kiểm tra mã nguồn app.js gọi đúng các endpoint Phase 4.3
    assert 'api("GET", "/api/v1/watchlist")' in js_text
    assert 'api("POST", "/api/v1/watchlist"' in js_text
    assert 'api("PATCH", "/api/v1/watchlist/"' in js_text
    assert 'api("DELETE", "/api/v1/watchlist/"' in js_text
    assert "alert_threshold_pct" in js_text

    # 2. Kiểm tra chuỗi tương tác API thực tế
    client = TestClient(app)
    uid = uuid.uuid4().hex[:8]
    user_test = f"phase4_wl_{uid}"
    user_other = f"phase4_wl_other_{uid}"

    # 2.1 Trạng thái ban đầu: user_test chưa có mã nào
    init_res = client.get("/api/v1/watchlist", headers={"X-User-ID": user_test})
    assert init_res.status_code == 200
    assert init_res.json()["count"] == 0

    # 2.2 Thêm mã TCB với alert_threshold_pct = 4.5%
    add_res = client.post(
        "/api/v1/watchlist",
        headers={"X-User-ID": user_test},
        json={"symbol": "TCB", "alert_threshold_pct": 4.5},
    )
    assert add_res.status_code == 200
    add_data = add_res.json()
    assert add_data["symbol"] == "TCB"
    assert add_data["threshold_pct"] == 4.5
    assert add_data.get("alert_threshold_pct") == 4.5

    # 2.3 Thêm mã SSI với threshold_pct = 3.0%
    add_ssi = client.post(
        "/api/v1/watchlist",
        headers={"X-User-ID": user_test},
        json={"symbol": "SSI", "threshold_pct": 3.0},
    )
    assert add_ssi.status_code == 200

    # 2.4 Nạp danh sách qua GET /api/v1/watchlist
    list_res = client.get("/api/v1/watchlist", headers={"X-User-ID": user_test})
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["count"] == 2
    sym_map = {item["symbol"]: item for item in list_data["items"]}
    assert "TCB" in sym_map
    assert "SSI" in sym_map
    assert sym_map["TCB"]["alert_threshold_pct"] == 4.5

    # 2.5 Cập nhật ngưỡng biến động TCB lên 5.5% qua PATCH /api/v1/watchlist/TCB
    patch_res = client.patch(
        "/api/v1/watchlist/TCB",
        headers={"X-User-ID": user_test},
        json={"alert_threshold_pct": 5.5},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["threshold_pct"] == 5.5
    assert patch_res.json().get("alert_threshold_pct") == 5.5

    # 2.6 Kiểm tra cô lập dữ liệu với user khác (Multi-tenant)
    other_res = client.get("/api/v1/watchlist", headers={"X-User-ID": user_other})
    assert other_res.status_code == 200
    assert other_res.json()["count"] == 0

    # 2.7 Xóa mã TCB qua DELETE /api/v1/watchlist/TCB
    del_res = client.delete("/api/v1/watchlist/TCB", headers={"X-User-ID": user_test})
    assert del_res.status_code == 200
    assert del_res.json()["ok"] is True

    # 2.8 Kiểm tra lại sau khi xóa: chỉ còn SSI
    after_del_res = client.get("/api/v1/watchlist", headers={"X-User-ID": user_test})
    assert after_del_res.status_code == 200
    after_data = after_del_res.json()
    assert after_data["count"] == 1
    assert after_data["items"][0]["symbol"] == "SSI"


def test_phase4_market_matrix_api_integration():
    """Phase 4.4: Kiểm tra tích hợp Market Matrix 10D API & Sparklines SVG.

    Xác nhận:
    1. Web UI app.js và index.html:
       - index.html có đủ cấu trúc #market-matrix-view, #market-matrix-table, #btn-refresh-matrix.
       - app.js chứa hàm loadMarketMatrix() gọi GET /api/v1/market/matrix-10d, renderMarketMatrix(), generateSparklineSvg().
    2. Endpoint GET /api/v1/market/matrix-10d và alias /api/v1/market/matrix:
       - Trả về đủ 10 mã VN30 mặc định.
       - Mỗi mã chứa current_price, change_pct, total_volume, sparkline (10 điểm float), và 10 sessions OHLCV.
       - Hỗ trợ tham số tùy biến symbols và days (ví dụ days=5).
    3. Kiểm thử logic sinh SVG Sparkline qua Node.js (nếu có môi trường Node).
    """
    import shutil
    import subprocess
    from fastapi.testclient import TestClient
    from backend.main import app

    html_text = (FE / "index.html").read_text(encoding="utf-8")
    js_text = (FE / "app.js").read_text(encoding="utf-8")

    # 1. Kiểm tra cấu trúc giao diện HTML & JS
    assert 'id="market-matrix-view"' in html_text
    assert 'id="market-matrix-table"' in html_text
    assert 'id="btn-refresh-matrix"' in html_text
    assert 'id="matrix-updated-time"' in html_text

    assert 'api("GET", "/api/v1/market/matrix-10d")' in js_text
    assert "renderMarketMatrix" in js_text
    assert "generateSparklineSvg" in js_text
    assert "loadMarketMatrix" in js_text
    assert "switchView" in js_text

    # 2. Kiểm tra API Backend
    client = TestClient(app)

    # 2.1 GET /api/v1/market/matrix-10d mặc định
    res = client.get("/api/v1/market/matrix-10d")
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert data["count"] == 10
    assert len(data["items"]) == 10

    for item in data["items"]:
        assert isinstance(item["symbol"], str) and len(item["symbol"]) == 3
        assert isinstance(item["current_price"], (int, float)) and item["current_price"] > 0
        assert isinstance(item["total_volume"], int) and item["total_volume"] >= 0
        assert isinstance(item["sparkline"], list)
        assert len(item["sparkline"]) == 10
        assert isinstance(item["sessions"], list)
        assert len(item["sessions"]) == 10
        for s in item["sessions"]:
            assert "date" in s
            assert "close" in s
            assert s["close"] > 0

    # 2.2 GET /api/v1/market/matrix (alias route)
    alias_res = client.get("/api/v1/market/matrix")
    assert alias_res.status_code == 200
    alias_data = alias_res.json()
    assert alias_data["count"] == 10
    assert len(alias_data["items"]) == 10

    # 2.3 Query tùy biến: symbols=FPT,VNM&days=5
    custom_res = client.get("/api/v1/market/matrix-10d?symbols=FPT,VNM&days=5")
    assert custom_res.status_code == 200
    custom_data = custom_res.json()
    assert custom_data["count"] == 2
    assert len(custom_data["items"]) == 2
    for item in custom_data["items"]:
        assert item["symbol"] in ("FPT", "VNM")
        assert len(item["sparkline"]) == 5
        assert len(item["sessions"]) == 5

    # 3. Kiểm thử hàm generateSparklineSvg qua Node.js nếu có sẵn
    node_bin = shutil.which("node")
    if node_bin:
        js_code = r"""
        const fs = require('fs');
        const code = fs.readFileSync('src/frontend/app.js', 'utf-8');
        const start = code.indexOf('function generateSparklineSvg');
        const end = code.indexOf('function renderMarketMatrix');
        if (start === -1 || end === -1) throw new Error("Could not find generateSparklineSvg");
        const snippet = code.slice(start, end);
        const fn = new Function(snippet + '; return generateSparklineSvg;');
        const generateSparklineSvg = fn();

        const svg = generateSparklineSvg([100, 105, 102, 108, 112]);
        if (!svg.includes('<svg') || !svg.includes('<polyline') || !svg.includes('<circle')) {
            throw new Error("Invalid sparkline SVG structure: " + svg);
        }
        if (!svg.includes('stroke="#059669"')) {
            throw new Error("Uptrend sparkline should have green stroke #059669");
        }

        const downSvg = generateSparklineSvg([120, 115, 110, 105]);
        if (!downSvg.includes('stroke="#dc2626"')) {
            throw new Error("Downtrend sparkline should have red stroke #dc2626");
        }
        console.log("SPARKLINE_TEST_OK");
        """
        proc = subprocess.run([node_bin, "-e", js_code], cwd=str(ROOT), capture_output=True, text=True)
        assert proc.returncode == 0, f"Node sparkline test failed: {proc.stderr}"
        assert "SPARKLINE_TEST_OK" in proc.stdout

