"""Langfuse tracing — chat dùng dependency thật; monitoring tắt = no-op."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.portfolio_watch.ai_main import app
from src.portfolio_watch.infra.monitoring import tracing as tracing_mod
from src.portfolio_watch.infra.monitoring.tracing import reset_client_for_tests, trace_request
from src.portfolio_watch.shared.settings import settings


@pytest.fixture(autouse=True)
def _reset_tracing():
    reset_client_for_tests()
    yield
    reset_client_for_tests()


def test_trace_noop_when_disabled(monkeypatch):
    monkeypatch.setattr(settings, "monitoring_enabled", False)
    with trace_request("chat", "q", metadata={"turn": "t1"}) as box:
        box["output"] = "ok"
    assert tracing_mod._client is None


def test_v1_chat_ok_when_monitoring_off(real_deps, monkeypatch):
    monkeypatch.setattr(settings, "monitoring_enabled", False)
    resp = TestClient(app).post("/v1/chat", json={"question": "Giá FPT?"})
    assert resp.status_code == 200 and resp.json().get("answer")
