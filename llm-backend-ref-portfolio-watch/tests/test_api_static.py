"""Phase 3a — API/AI process không phục vụ static UI (UI = frontend/)."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from starlette.routing import Mount
from starlette.staticfiles import StaticFiles

from src.portfolio_watch.ai_main import app as ai_app
from src.portfolio_watch.main import app

ROOT = Path(__file__).resolve().parents[1]
client = TestClient(app)


def _has_static_mount(fastapi_app) -> bool:
    for route in fastapi_app.routes:
        if isinstance(route, Mount) and isinstance(route.app, StaticFiles):
            return True
    return False


def test_legacy_web_dir_still_on_disk():
    """web/ giữ để tham chiếu MVP; không còn mount vào process API/AI."""
    web = ROOT / "web"
    assert web.is_dir()
    assert (web / "index.html").is_file()
    assert (web / "app.js").is_file()
    assert (web / "style.css").is_file()


def test_monolith_app_has_no_static_web_mount():
    assert not _has_static_mount(app)
    resp = client.get("/")
    assert resp.status_code == 404
    assert client.get("/index.html").status_code == 404
    assert client.get("/app.js").status_code == 404
    assert client.get("/style.css").status_code == 404


def test_ai_app_has_no_static_web_mount():
    assert not _has_static_mount(ai_app)
    ai_client = TestClient(ai_app)
    assert ai_client.get("/").status_code == 404
    assert ai_client.get("/app.js").status_code == 404


def test_api_still_serves_json():
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


def test_frontend_process_owns_ui_assets():
    """UI sống ở frontend/ — process riêng (serve_frontend), không trên API."""
    fe = ROOT / "frontend"
    assert (fe / "index.html").is_file()
    html = (fe / "index.html").read_text(encoding="utf-8")
    assert 'id="chat"' in html
    assert 'id="timeline"' in html
    assert 'id="watchlist"' in html
    assert 'id="approvals"' in html
