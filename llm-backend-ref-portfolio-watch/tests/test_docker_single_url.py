"""Docker image = API only; UI không ship trong cùng container (Phase 3a)."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from starlette.routing import Mount
from starlette.staticfiles import StaticFiles

from src.portfolio_watch.main import app

ROOT = Path(__file__).resolve().parents[1]


def test_api_container_app_has_no_ui_mount():
    assert not any(
        isinstance(r, Mount) and isinstance(r.app, StaticFiles) for r in app.routes
    )
    client = TestClient(app)
    assert client.get("/").status_code == 404
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json() == {"status": "ok"}


def test_dockerfile_is_api_only_no_web_copy():
    df = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    # UI không mount trong AI app — FE là service compose riêng (COPY frontend)
    assert "COPY web" not in df
    assert "uvicorn" in df
    assert "ai_main" in df or "portfolio_watch.ai_main" in df
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert "8000" in compose
    assert "frontend:" in compose


def test_frontend_ui_lives_outside_api_image():
    assert (ROOT / "frontend" / "index.html").is_file()
