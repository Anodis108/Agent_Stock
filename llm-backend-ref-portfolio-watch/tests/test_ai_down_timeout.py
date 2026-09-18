"""Phase 5 — AI down / timeout → Backend 502 có message; FE không treo."""

from __future__ import annotations

import urllib.error
from pathlib import Path

from fastapi.testclient import TestClient

from backend import ai_client
from backend.ai_client import AiClientError, _is_timeout
from backend.main import app, store
from backend.store import WatchlistItem

FE = Path(__file__).resolve().parents[1] / "frontend"


def setup_function():
    store.clear()
    store.upsert_watchlist(WatchlistItem(symbol="FPT", threshold_pct=3.0))


def test_is_timeout_detects_urlerror_timed_out():
    exc = urllib.error.URLError(TimeoutError("timed out"))
    assert _is_timeout(exc) is True
    assert _is_timeout(TimeoutError()) is True
    assert _is_timeout(urllib.error.URLError("Connection refused")) is False


def test_backend_chat_ai_down_returns_502_with_message(monkeypatch):
    client = TestClient(app)

    def boom(**kwargs):
        raise AiClientError("AI không kết nối được: Connection refused")

    monkeypatch.setattr("backend.main.ai_chat", boom)
    resp = client.post("/chat", json={"question": "Giá FPT?"})
    assert resp.status_code == 502
    assert "AI" in resp.json()["detail"]
    assert "kết nối" in resp.json()["detail"].lower() or "AI" in resp.json()["detail"]


def test_backend_chat_ai_timeout_returns_502(monkeypatch):
    client = TestClient(app)

    def boom(**kwargs):
        raise AiClientError("AI timeout")

    monkeypatch.setattr("backend.main.ai_chat", boom)
    resp = client.post("/chat", json={"question": "Giá FPT?"})
    assert resp.status_code == 502
    assert "timeout" in resp.json()["detail"].lower()


def test_backend_scan_ai_down_returns_502(monkeypatch):
    client = TestClient(app)

    def boom(**kwargs):
        raise AiClientError("AI không kết nối được: refuse")

    monkeypatch.setattr("backend.main.ai_scan", boom)
    resp = client.post("/scan", json={"symbol": "FPT"})
    assert resp.status_code == 502
    assert "AI" in resp.json()["detail"]


def test_ai_client_timeout_env(monkeypatch):
    monkeypatch.setenv("AI_HTTP_TIMEOUT", "12.5")
    assert ai_client._default_timeout() == 12.5
    monkeypatch.setenv("AI_HTTP_TIMEOUT", "bad")
    assert ai_client._default_timeout() == 60.0


def test_frontend_handles_timeout_and_network_errors():
    js = (FE / "app.js").read_text(encoding="utf-8")
    cfg = (FE / "config.js").read_text(encoding="utf-8")
    assert "REQUEST_TIMEOUT_MS" in cfg
    assert "AbortController" in js
    assert "formatApiError" in js
    assert "showOpError" in js
    assert "Hết thời gian chờ" in js or "timeout" in js.lower()
    assert "Không nối được Backend" in js or "Failed to fetch" in js
    # nút Gửi luôn enable lại
    assert "sendBtn.disabled = false" in js
