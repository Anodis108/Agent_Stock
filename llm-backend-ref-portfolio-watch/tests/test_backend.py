"""Backend API — SQLite thật, proxy HTTP tới AI service thật."""

from __future__ import annotations

import ast
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.portfolio_watch.backend.main import app, store
from src.portfolio_watch.backend.store import ApprovalRecord, WatchlistItem

ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "src" / "portfolio_watch" / "backend"
_FORBIDDEN = ("domain.agents", "portfolio_watch.application", "langgraph", "langchain")


def setup_function():
    store.clear()
    store.upsert_watchlist(WatchlistItem(symbol="FPT", threshold_pct=3.0))


def test_backend_no_agent_imports():
    for path in BACKEND_DIR.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not any(f in alias.name for f in _FORBIDDEN), path
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                assert not any(f in mod for f in _FORBIDDEN), path


def test_health_watchlist_approvals():
    client = TestClient(app)
    assert client.get("/health").json()["service"] == "backend"
    assert client.get("/watchlist").json()["count"] >= 1

    created = client.post("/watchlist", json={"symbol": "vnm", "threshold_pct": 5.0})
    assert created.status_code == 200
    assert created.json()["symbol"] == "VNM"

    store.add_pending(
        ApprovalRecord(id="ap-1", user_id="default", symbol="FPT", gate="gate1")
    )
    assert client.get("/approvals").json()["count"] == 1
    assert client.post("/approvals/ap-1/approve", json={}).json()["ok"] is True


def test_chat_proxy_to_real_ai(ai_server_url, monkeypatch):
    monkeypatch.setenv("AI_BASE_URL", ai_server_url)
    client = TestClient(app)
    resp = client.post("/chat", json={"question": "Giá FPT hiện tại?"})
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("answer")
    assert body.get("request_id")
    assert isinstance(body.get("steps"), list) and len(body["steps"]) >= 1


def test_ai_down_returns_502(monkeypatch):
    monkeypatch.setenv("AI_BASE_URL", "http://127.0.0.1:59999")
    client = TestClient(app)
    resp = client.post("/chat", json={"question": "Giá FPT?"})
    assert resp.status_code == 502
