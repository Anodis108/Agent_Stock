"""Phase 7 — API + static web/ cùng một URL trong container (localhost:8000)."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from src.portfolio_watch.main import WEB_DIR, app, resolve_web_dir

ROOT = Path(__file__).resolve().parents[1]


def test_resolve_web_dir_finds_project_web():
    found = resolve_web_dir()
    assert found.is_dir()
    assert (found / "index.html").is_file()
    assert WEB_DIR == found


def test_single_origin_api_and_ui_same_base():
    """Demo chỉ cần http://localhost:8000 — UI + /health + API."""
    client = TestClient(app)
    ui = client.get("/")
    assert ui.status_code == 200
    assert 'id="chat"' in ui.text

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json() == {"status": "ok"}

    js = client.get("/app.js")
    assert js.status_code == 200
    assert 'API_BASE = ""' in js.text  # cùng origin, không URL API riêng


def test_dockerfile_ships_web_for_single_url_demo():
    df = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "COPY web" in df
    assert "uvicorn" in df and "src.portfolio_watch.main:app" in df
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert "8000" in compose


def test_docker_editable_layout_web_beside_src(tmp_path):
    """Editable Docker: /app/src/portfolio_watch/main.py → /app/web."""
    app_root = tmp_path / "app"
    web = app_root / "web"
    web.mkdir(parents=True)
    (web / "index.html").write_text("<html>ok</html>", encoding="utf-8")
    pkg = app_root / "src" / "portfolio_watch"
    pkg.mkdir(parents=True)
    fake_main = pkg / "main.py"
    fake_main.write_text("# fake", encoding="utf-8")
    cand = fake_main.resolve().parents[2] / "web"
    assert cand.is_dir()
    assert (cand / "index.html").is_file()
