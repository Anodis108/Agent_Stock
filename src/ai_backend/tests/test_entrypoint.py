"""Tests for Phase 3.5: AI Shared & Entrypoint (main.py, settings.py, exceptions.py, charts.py)."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ai_backend.main import app
from ai_backend.shared.charts import apply_chart_style, get_charts_dir
from ai_backend.shared.exceptions import (
    AiBackendException,
    GuardrailViolation,
    LLMTimeoutException,
    ModelProviderException,
    PromptTemplateException,
    QdrantUnavailableException,
    RedisUnavailableException,
    ScanExecutionException,
)
from ai_backend.shared.settings import AiSettings, ai_settings


def test_ai_settings_defaults():
    """Kiểm tra giá trị mặc định của AiSettings."""
    settings = AiSettings()
    assert settings.port == 8001
    assert settings.host == "0.0.0.0"
    assert settings.qdrant_collection == "stock_concepts"
    assert settings.llm_backend == "mock"
    assert settings.price_fallback_on_error is True
    assert ai_settings.port in (8001, int(os.environ.get("AI_PORT", 8001)))


def test_ai_settings_load_env_override():
    """Kiểm tra cơ chế nạp đè qua biến môi trường."""
    with patch.dict(
        os.environ,
        {
            "AI_PORT": "8888",
            "AI_HOST": "127.0.0.1",
            "LLM_BACKEND": "deepseek",
            "PRICE_FALLBACK_ON_ERROR": "false",
        },
    ):
        custom = AiSettings.load()
        assert custom.port == 8888
        assert custom.host == "127.0.0.1"
        assert custom.llm_backend == "deepseek"
        assert custom.price_fallback_on_error is False


def test_ai_backend_exceptions():
    """Kiểm tra hệ thống phân cấp ngoại lệ của AI Backend."""
    base_err = AiBackendException("Base error", status_code=500)
    assert base_err.status_code == 500
    assert str(base_err) == "Base error"

    guard_err = GuardrailViolation(
        message="Chặn prompt injection", category="injection", detail="Detect malicious pattern"
    )
    assert guard_err.status_code == 400
    assert guard_err.category == "injection"
    assert guard_err.detail == "Detect malicious pattern"

    timeout_err = LLMTimeoutException(timeout_seconds=45.0)
    assert timeout_err.status_code == 504
    assert timeout_err.timeout_seconds == 45.0

    provider_err = ModelProviderException(message="Quota exceeded", provider="openai")
    assert provider_err.status_code == 502
    assert provider_err.provider == "openai"

    qdrant_err = QdrantUnavailableException()
    assert qdrant_err.status_code == 503

    redis_err = RedisUnavailableException()
    assert redis_err.status_code == 503

    prompt_err = PromptTemplateException("Template missing")
    assert prompt_err.status_code == 500

    scan_err = ScanExecutionException("HPG", "Indicator failure")
    assert scan_err.status_code == 500
    assert scan_err.symbol == "HPG"


def test_charts_dir_and_style():
    """Kiểm tra hàm get_charts_dir và áp dụng style Matplotlib."""
    charts_dir = get_charts_dir()
    assert isinstance(charts_dir, Path)
    assert charts_dir.is_dir()

    # Không gây lỗi khi áp dụng style dark/light
    apply_chart_style(dark_mode=True)
    apply_chart_style(dark_mode=False)


def test_ai_main_health_endpoint():
    """Kiểm tra endpoint GET /health của AI Backend Microservice."""
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "ai_backend"
    assert data["port"] == 8001
    assert data["swarm"] == "ready"
    assert "timestamp" in data
    assert "x-correlation-id" in response.headers


def test_ai_main_chat_stream_endpoint():
    """Kiểm tra endpoint POST /v1/chat/stream phát SSE."""
    client = TestClient(app)
    payload = {
        "question": "Chào bạn, hãy giới thiệu thị trường",
        "user_id": "test_user",
        "request_id": "req-12345",
    }
    response = client.post("/v1/chat/stream", json=payload)
    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")
    assert "node_start" in response.text
    assert "node_finish" in response.text


def test_ai_main_scan_endpoint():
    """Kiểm tra endpoint POST /v1/scan phân tích kỹ thuật."""
    client = TestClient(app)
    payload = {
        "symbol": "VNM",
        "user_id": "test_user",
        "threshold_pct": 3.0,
    }
    response = client.post("/v1/scan", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "VNM"
    assert "alerts" in data
    assert "steps" in data


def test_ai_main_guardrail_exception_handler():
    """Kiểm tra exception handler bắt GuardrailViolation và trả HTTP 400."""
    test_app = FastAPI()
    from ai_backend.api.helpers.exception_handler import register_ai_exception_handlers
    register_ai_exception_handlers(test_app)

    @test_app.get("/trigger-guardrail")
    def trigger_guardrail():
        raise GuardrailViolation(
            message="Chặn Prompt Injection độc hại",
            category="injection",
            detail="Forbidden instruction pattern detected",
        )

    client = TestClient(test_app)
    resp = client.get("/trigger-guardrail")
    assert resp.status_code == 400
    data = resp.json()
    assert data["error"] == "Chặn Prompt Injection độc hại"
    assert data["category"] == "injection"
    assert data["detail"] == "Forbidden instruction pattern detected"
    assert data["service"] == "ai_backend"


def test_ai_main_llm_timeout_exception_handler():
    """Kiểm tra exception handler bắt LLMTimeoutException và trả HTTP 504."""
    test_app = FastAPI()
    from ai_backend.api.helpers.exception_handler import register_ai_exception_handlers
    register_ai_exception_handlers(test_app)

    @test_app.get("/trigger-timeout")
    def trigger_timeout():
        raise LLMTimeoutException("OpenAI timeout after 30s", timeout_seconds=30.0)

    client = TestClient(test_app)
    resp = client.get("/trigger-timeout")
    assert resp.status_code == 504
    data = resp.json()
    assert "timeout" in data["error"].lower()
    assert data["service"] == "ai_backend"
