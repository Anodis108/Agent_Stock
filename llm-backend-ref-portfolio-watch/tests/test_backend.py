"""Backend / product API — SQLite; AI mặc định in-process (Phase 2)."""

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
# Phase 2: ai_client được phép gọi application layer (in-process LangGraph).
# Vẫn cấm portfolio_watch.agents / domain.agents / langchain trực tiếp trong backend (trừ lazy trong ai_client).
_FORBIDDEN_EVERYWHERE = ("portfolio_watch.agents", "domain.agents")
_FORBIDDEN_EXCEPT_AI_CLIENT = ("langgraph", "langchain")


def setup_function():
    store.clear()
    store.upsert_watchlist(WatchlistItem(symbol="FPT", threshold_pct=3.0))


def test_backend_no_agent_imports():
    for path in BACKEND_DIR.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            for name in names:
                assert not any(f in name for f in _FORBIDDEN_EVERYWHERE), path
                if path.name != "ai_client.py":
                    assert not any(f in name for f in _FORBIDDEN_EXCEPT_AI_CLIENT), path


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


def test_ui_index_served():
    """Một process phục vụ UI static (Phase 2)."""
    client = TestClient(app)
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")
    body = resp.text
    assert "Frontend tách riêng" not in body
    assert "cùng origin" in body or "Portfolio Watch" in body
    for asset in ("/app.js", "/config.js", "/style.css"):
        assert client.get(asset).status_code == 200
    # API không bị StaticFiles nuốt
    assert client.get("/health").status_code == 200
    assert client.get("/watchlist").status_code == 200
    assert client.get("/approvals").status_code == 200


def test_config_same_origin_default():
    client = TestClient(app)
    cfg = client.get("/config.js")
    assert cfg.status_code == 200
    assert 'BACKEND_BASE_URL: ""' in cfg.text or "BACKEND_BASE_URL: ''" in cfg.text


def test_chat_inprocess(real_deps, monkeypatch):
    monkeypatch.delenv("AI_TRANSPORT", raising=False)
    client = TestClient(app)
    resp = client.post("/chat", json={"question": "Giá FPT hiện tại?"})
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("answer")
    assert body.get("request_id")
    assert isinstance(body.get("steps"), list) and len(body["steps"]) >= 1
    assert any("input" in s for s in body["steps"])
    assert any("output" in s for s in body["steps"])


def test_chat_proxy_http_to_real_ai(ai_server_url, monkeypatch):
    monkeypatch.setenv("AI_TRANSPORT", "http")
    monkeypatch.setenv("AI_BASE_URL", ai_server_url)
    client = TestClient(app)
    resp = client.post("/chat", json={"question": "Giá FPT hiện tại?"})
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("answer")
    assert body.get("request_id")
    assert isinstance(body.get("steps"), list) and len(body["steps"]) >= 1


def test_ai_http_down_returns_502(monkeypatch):
    monkeypatch.setenv("AI_TRANSPORT", "http")
    monkeypatch.setenv("AI_BASE_URL", "http://127.0.0.1:59999")
    client = TestClient(app)
    resp = client.post("/chat", json={"question": "Giá FPT?"})
    assert resp.status_code == 502


def test_normalize_steps_preserves_input_output():
    from src.portfolio_watch.backend.steps import normalize_steps

    raw = [
        {
            "id": "1",
            "name": "rewrite_question",
            "status": "done",
            "detail": "Giá FPT",
            "input": {"question": "Giá FPT hôm nay?"},
            "output": {"rewritten": "Giá FPT hôm nay?", "symbol": "FPT"},
        },
        {
            "name": "price_agent",
            "status": "done",
            "input": {"symbol": "FPT"},
            "output": {"symbol": "FPT", "latest_close": 120.5},
        },
    ]
    normalized = normalize_steps(raw)
    assert len(normalized) == 2
    assert normalized[0]["input"] == {"question": "Giá FPT hôm nay?"}
    assert normalized[0]["output"]["symbol"] == "FPT"
    assert normalized[1]["input"] == {"symbol": "FPT"}
    assert normalized[1]["output"]["latest_close"] == 120.5


def test_build_steps_from_chunks_populates_io():
    from src.portfolio_watch.agents.supervisor_agent import RewrittenQuestion
    from src.portfolio_watch.graph.steps import build_steps_from_chunks

    chunks = [
        {
            "rewrite_question": {
                "rewritten": RewrittenQuestion(
                    original="fpt?",
                    rewritten="Giá FPT?",
                    symbol="FPT",
                    intent="price_lookup",
                )
            }
        }
    ]
    steps = build_steps_from_chunks(chunks)
    assert len(steps) == 1
    assert steps[0]["name"] == "rewrite_question"
    assert steps[0]["input"] == {"question": "fpt?"}
    assert steps[0]["output"]["symbol"] == "FPT"

def test_phase13_single_app_endpoints():
    client = TestClient(app)
    assert client.get("/health").status_code == 200
    assert client.get("/watchlist").status_code == 200
    assert client.get("/market").status_code == 200
    assert client.get("/approvals").status_code == 200


def test_phase13_scan_and_approve_api():
    """Flow C: approve/reject API + market phản ánh pending (store-only, nhanh)."""
    client = TestClient(app)
    store.add_pending(
        ApprovalRecord(id="ap-p13", user_id="default", symbol="FPT", gate="gate1")
    )
    assert client.get("/approvals").json()["count"] == 1
    market_before = client.get("/market").json()
    assert any(i["symbol"] == "FPT" and i["status"] == "pending" for i in market_before["items"])

    ok = client.post("/approvals/ap-p13/approve", json={"user_id": "default"})
    assert ok.status_code == 200
    assert ok.json()["ok"] is True
    assert client.get("/approvals").json()["count"] == 0

    store.add_pending(
        ApprovalRecord(id="ap-p13b", user_id="default", symbol="VNM", gate="gate1")
    )
    store.upsert_watchlist(WatchlistItem(symbol="VNM", threshold_pct=3.0))
    rej = client.post(
        "/approvals/ap-p13b/reject",
        json={"user_id": "default", "reason": "tin nhiễu"},
    )
    assert rej.status_code == 200
    assert rej.json()["ok"] is True
    assert client.get("/approvals").json()["count"] == 0
