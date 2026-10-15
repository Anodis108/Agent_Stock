"""Unit tests for Web Backend Main Entrypoint and Shared Settings."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from web_backend.main import app
from web_backend.shared.exceptions import (
    AiServiceUnavailableException,
    HoldingNotFoundException,
    SessionNotFoundException,
    ValidationException,
    WebBackendException,
    WebDatabaseException,
)
from web_backend.shared.settings import WebSettings, web_settings


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


class TestWebSettings:
    """Kiểm tra nạp cấu hình WebSettings."""

    def test_web_settings_defaults(self) -> None:
        assert web_settings.port in (8000, 8001, 8080)
        assert web_settings.host in ("0.0.0.0", "127.0.0.1", "localhost")
        assert "http" in web_settings.ai_base_url

    def test_web_settings_load_override(self) -> None:
        with patch.dict("os.environ", {"PORT": "8888", "AI_BASE_URL": "http://test-ai:8001"}):
            settings = WebSettings.load()
            assert settings.port == 8888
            assert settings.ai_base_url == "http://test-ai:8001"


class TestWebExceptions:
    """Kiểm tra phân cấp ngoại lệ của Web Backend."""

    def test_exceptions_status_codes(self) -> None:
        db_err = WebDatabaseException("Lỗi DB")
        assert db_err.status_code == 500

        sess_err = SessionNotFoundException("sess-123")
        assert sess_err.status_code == 404
        assert "sess-123" in sess_err.message

        h_err = HoldingNotFoundException("holding-1")
        assert h_err.status_code == 404

        val_err = ValidationException("Dữ liệu sai")
        assert val_err.status_code == 422

        ai_err = AiServiceUnavailableException("AI chết")
        assert ai_err.status_code == 503


class TestMainApp:
    """Kiểm tra hoạt động của FastAPI application trong main.py."""

    def test_health_check_endpoint(self, client: TestClient) -> None:
        with patch("web_backend.main.RemoteAiClient.check_health") as mock_health:
            mock_health.return_value = {"status": "ok", "service": "ai_backend"}
            resp = client.get("/health")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "ok"
            assert data["service"] == "web_backend"
            assert data["ai_backend"]["status"] == "ok"

    def test_correlation_id_in_response(self, client: TestClient) -> None:
        resp = client.get("/health", headers={"X-Correlation-ID": "test-corr-123"})
        assert resp.status_code == 200
        assert resp.headers.get("x-correlation-id") == "test-corr-123"

    def test_all_expected_routes_registered(self) -> None:
        paths = set(app.openapi()["paths"].keys())
        expected_paths = [
            "/health",
            "/chat",
            "/api/v1/sessions",
            "/watchlist",
            "/approvals/review",
            "/scan",
            "/api/portfolio/holdings",
            "/api/market/sessions",
        ]
        for path in expected_paths:
            assert path in paths, f"Route {path} should be registered in main:app"

    def test_root_endpoint(self, client: TestClient) -> None:
        resp = client.get("/")
        assert resp.status_code == 200
