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


def test_dockerfile_and_dockerignore_keep_secrets_out_of_image():
    df = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    ignore = (ROOT / ".dockerignore").read_text(encoding="utf-8")
    assert "OPENAI_API_KEYS=" not in df or "OPENAI_API_KEYS=sk" not in df
    assert "sk-proj" not in df
    assert ".env" in ignore
