"""Docker product — compose, Dockerfile, env."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from backend.backend.main import app as product_app

ROOT = Path(__file__).resolve().parents[1]


def test_compose_two_services_backend_and_frontend_and_volume():
    text = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert "\n  backend:" in text
    assert "\n  frontend:" in text
    assert "qdrant" in text
    assert "profiles:" in text
    assert "pw_data:/app/data" in text
    assert "SQLITE_PATH: /app/data/portfolio_watch.db" in text
    assert "BACKEND_SQLITE_PATH: /app/data/backend_store.db" in text
    assert "backend.backend.main" in text
    assert "healthcheck:" in text
    assert "AI_TRANSPORT" in text
    assert "LANGFUSE_HOST" in text
    assert "sk-" not in text.lower()


def test_dockerfile_and_frontend_dockerfile():
    df_path = ROOT / "src" / "backend" / "Dockerfile" if (ROOT / "src" / "backend" / "Dockerfile").is_file() else ROOT / "Dockerfile"
    df = df_path.read_text(encoding="utf-8")
    assert "backend.backend.main:app" in df
    fe_df_path = ROOT / "src" / "frontend" / "Dockerfile" if (ROOT / "src" / "frontend" / "Dockerfile").is_file() else ROOT / "frontend" / "Dockerfile"
    fe_df = fe_df_path.read_text(encoding="utf-8")
    assert "nginx" in fe_df
    assert (ROOT / "src" / "frontend" / "nginx.conf").is_file() or (ROOT / "frontend" / "nginx.conf").is_file()


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


def test_product_app_serves_health_and_ui():
    assert (ROOT / "src" / "frontend" / "index.html").is_file() or (ROOT / "frontend" / "index.html").is_file() or (ROOT / "src" / "portfolio_watch" / "frontend" / "index.html").is_file()
    client = TestClient(product_app)
    assert client.get("/health").status_code == 200
    assert client.get("/").status_code == 200


def test_phase13_inprocess_default(monkeypatch):
    """Mặc định product: AI in-process, không bắt buộc service :8001."""
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    env_ex = (ROOT / ".env.example").read_text(encoding="utf-8")
    assert 'AI_TRANSPORT: "inprocess"' in compose
    assert "AI_TRANSPORT=inprocess" in env_ex
    assert "\n  ai:" not in compose

    from backend.backend.ai_client import _use_http

    monkeypatch.delenv("AI_TRANSPORT", raising=False)
    assert _use_http() is False
    monkeypatch.setenv("AI_TRANSPORT", "http")
    assert _use_http() is True
