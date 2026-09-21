"""Docker product — compose, Dockerfile, env."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from src.portfolio_watch.main import app

ROOT = Path(__file__).resolve().parents[1]


def test_compose_three_services_and_volume():
    text = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert "ai:" in text and "backend:" in text and "frontend:" in text
    assert "pw_data:/app/data" in text
    assert "SQLITE_PATH: /app/data/portfolio_watch.db" in text
    assert "BACKEND_SQLITE_PATH: /app/data/backend_store.db" in text
    assert "src.portfolio_watch.backend.main" in text
    assert "src/portfolio_watch/frontend" in text
    assert "healthcheck:" in text
    assert "LANGFUSE_HOST" in text
    assert "sk-" not in text.lower()


def test_dockerfile_src_only():
    df = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "COPY src" in df
    assert "COPY backend" not in df
    assert "COPY frontend" not in df
    assert "ai_main" in df
    assert "portfolio-watch:split" in (ROOT / "docker-compose.yml").read_text(
        encoding="utf-8"
    )


def test_env_example_has_langfuse_and_compose_vars():
    text = (ROOT / ".env.example").read_text(encoding="utf-8")
    for key in (
        "MONITORING_ENABLED",
        "LANGFUSE_PUBLIC_KEY",
        "LANGFUSE_SECRET_KEY",
        "LANGFUSE_HOST",
        "APP_HOST_PORT",
    ):
        assert key in text


def test_frontend_static_outside_api_container():
    assert (ROOT / "src" / "portfolio_watch" / "frontend" / "index.html").is_file()
    client = TestClient(app)
    assert client.get("/health").status_code == 200
    assert client.get("/").status_code == 404
