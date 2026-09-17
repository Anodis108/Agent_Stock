from __future__ import annotations

import re

from fastapi.testclient import TestClient

from src.portfolio_watch.main import WEB_DIR, app

client = TestClient(app)


def test_web_dir_exists():
    assert WEB_DIR.is_dir()
    assert (WEB_DIR / "index.html").is_file()
    assert (WEB_DIR / "app.js").is_file()
    assert (WEB_DIR / "style.css").is_file()


def test_serve_index_same_origin():
    """product-spec Frontend: 1 trang chat + watchlist + approvals tại cùng origin."""
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")
    body = resp.text
    assert "Portfolio Watch" in body
    assert 'id="chat"' in body
    assert 'id="watchlist"' in body
    assert 'id="approvals"' in body

    # /index.html cũng phục vụ được (bookmark / link trực tiếp)
    resp2 = client.get("/index.html")
    assert resp2.status_code == 200
    assert "Portfolio Watch" in resp2.text


def test_html_asset_links_resolve_same_origin():
    """style.css / app.js relative từ index → cùng base URL với API."""
    html = client.get("/").text
    assets = re.findall(r'(?:href|src)="([^"]+)"', html)
    for href in assets:
        if href.startswith("data:"):
            continue
        path = href if href.startswith("/") else f"/{href}"
        resp = client.get(path)
        assert resp.status_code == 200, path


def test_serve_static_assets():
    js = client.get("/app.js")
    assert js.status_code == 200
    assert "apiFetch" in js.text or "API_BASE" in js.text

    css = client.get("/style.css")
    assert css.status_code == 200
    assert len(css.text) > 0


def test_ui_wiring_renders_scan_chat_approvals():
    """Phase 4: app.js không còn log-only; scan hiện đủ luồng AC."""
    html = client.get("/").text
    assert 'id="scan-form"' in html
    assert 'id="watchlist-body"' in html
    assert 'id="approvals-list"' in html
    assert "sample-1" not in html  # không còn placeholder HITL mẫu

    js = client.get("/app.js").text
    assert 'API_BASE = ""' in js
    assert "refreshWatchlist" in js
    assert "refreshApprovals" in js
    assert "appendChat" in js
    assert "showScanResult" in js
    assert "severity" in js and "news" in js
    assert "Phase 2" not in js
    assert "stubs ready" not in js


def test_api_not_shadowed_by_static_mount():
    """Mount `/` không che API — cùng base URL, JSON vẫn đúng."""
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json() == {"status": "ok"}

    wl = client.get("/watchlist")
    assert wl.status_code == 200
    assert "application/json" in wl.headers.get("content-type", "")
    assert "items" in wl.json()

    ap = client.get("/approvals")
    assert ap.status_code == 200
    assert "application/json" in ap.headers.get("content-type", "")
    assert "items" in ap.json()

    assert "/scan" in app.openapi()["paths"]
    assert "/chat" in app.openapi()["paths"]
    assert client.get("/docs").status_code == 200
