"""Phase 7 — container đọc .env via env_file; .env.example có biến Docker."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_compose_uses_env_file_not_hardcoded_secrets():
    text = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert "env_file:" in text
    assert ".env" in text
    assert "APP_HOST_PORT" in text
    assert "SQLITE_PATH" in text
    assert "/app/data/portfolio_watch.db" in text
    assert "API_HOST" in text and "0.0.0.0" in text
    assert "sk-" not in text.lower()
    assert "OPENAI_API_KEYS=sk" not in text


def test_env_example_documents_docker_vars():
    text = (ROOT / ".env.example").read_text(encoding="utf-8")
    assert "OPENAI_API_KEYS" in text
    assert "APP_HOST_PORT" in text
    assert "SQLITE_PATH" in text
    assert "/app/data" in text or "Docker" in text or "docker" in text
    assert "API_HOST" in text


def test_env_example_split_deploy_and_langfuse_vars():
    """Phase 1 — URL 3 process + giữ Langfuse / OpenAI keys."""
    text = (ROOT / ".env.example").read_text(encoding="utf-8")
    for key in (
        "AI_BASE_URL",
        "BACKEND_BASE_URL",
        "FRONTEND_ORIGIN",
        "APP_HOST_PORT",
        "OPENAI_API_KEYS",
        "MONITORING_ENABLED",
        "LANGFUSE_PUBLIC_KEY",
        "LANGFUSE_SECRET_KEY",
        "LANGFUSE_HOST",
    ):
        assert key in text, f"missing {key} in .env.example"


def test_settings_loads_split_deploy_defaults():
    from src.portfolio_watch.shared.settings import settings

    assert settings.ai_base_url.startswith("http")
    assert "8001" in settings.ai_base_url
    assert settings.backend_base_url.startswith("http")
    assert "8000" in settings.backend_base_url
    assert "5173" in settings.frontend_origin
    assert settings.app_host_port == 8000


def test_dockerfile_and_dockerignore_keep_secrets_out_of_image():
    df = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    ignore = (ROOT / ".dockerignore").read_text(encoding="utf-8")
    assert "OPENAI_API_KEYS=" not in df or "OPENAI_API_KEYS=sk" not in df
    assert "sk-proj" not in df
    assert ".env" in ignore
