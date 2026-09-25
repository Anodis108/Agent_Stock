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

    fe_df_path = ROOT / "src" / "frontend" / "Dockerfile" if (ROOT / "src" / "frontend" / "Dockerfile").is_file() else ROOT / "frontend" / "Dockerfile"
    fe_df = fe_df_path.read_text(encoding="utf-8")
    assert "nginx" in fe_df
    assert (ROOT / "src" / "frontend" / "nginx.conf").is_file() or (ROOT / "frontend" / "nginx.conf").is_file()


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


# ==============================================================================
# 5. Documentation & README Consistency Tests
# ==============================================================================

def test_readme_docker_product_and_local():
    """Kiểm tra README.md có hướng dẫn Docker Compose và chạy Local đầy đủ."""
    content = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "docker compose up --build" in content
    assert "uvicorn backend.main" in content or "uvicorn backend.backend.main" in content or "python -m backend.main" in content
