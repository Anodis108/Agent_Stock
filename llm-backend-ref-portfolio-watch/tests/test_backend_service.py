"""Phase 3b — Backend health, watchlist, approvals, proxy AI (HTTP only)."""

from __future__ import annotations

import ast
from pathlib import Path

from fastapi.testclient import TestClient

from backend import ai_client
from backend.main import app, store
from backend.store import ApprovalRecord

ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"


def setup_function():
    store.clear()
    from backend.store import WatchlistItem

    store.upsert_watchlist(WatchlistItem(symbol="FPT", threshold_pct=3.0))


def test_backend_has_no_domain_agents_import():
    """Giữ assert nhanh trong suite service; chi tiết ở test_backend_no_agent_imports."""
    forbidden = (
        "domain.agents",
        "portfolio_watch.application",
        "langgraph",
    )
    for path in BACKEND_DIR.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not any(f in alias.name for f in forbidden), path
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                assert not any(f in mod for f in forbidden), path
                assert not mod.startswith("src.portfolio_watch"), path


def test_health_and_watchlist_crud():
    client = TestClient(app)
    h = client.get("/health")
    assert h.status_code == 200
    assert h.json()["service"] == "backend"

    wl = client.get("/watchlist").json()
    assert wl["count"] >= 1
    assert any(i["symbol"] == "FPT" for i in wl["items"])

    created = client.post("/watchlist", json={"symbol": "vnm", "threshold_pct": 5.0})
    assert created.status_code == 200
    assert created.json()["symbol"] == "VNM"
    assert created.json()["threshold_pct"] == 5.0

    patched = client.patch("/watchlist/VNM", json={"threshold_pct": 4.0})
    assert patched.status_code == 200
    assert patched.json()["threshold_pct"] == 4.0

    deleted = client.delete("/watchlist/VNM")
    assert deleted.status_code == 200
    assert deleted.json()["ok"] is True


def test_approvals_approve_reject():
    client = TestClient(app)
    store.add_pending(
        ApprovalRecord(id="ap-1", user_id="default", symbol="FPT", gate="gate1")
    )
    listed = client.get("/approvals").json()
    assert listed["count"] == 1

    ok = client.post("/approvals/ap-1/approve", json={})
    assert ok.status_code == 200
    assert ok.json()["ok"] is True
    assert client.get("/approvals").json()["count"] == 0

    store.add_pending(
        ApprovalRecord(id="ap-2", user_id="default", symbol="HPG", gate="gate1")
    )
    rej = client.post(
        "/approvals/ap-2/reject", json={"reason": "không cần cảnh báo"}
    )
    assert rej.status_code == 200
    assert rej.json()["action"] == "reject"


def test_chat_and_scan_proxy_to_ai(monkeypatch):
    client = TestClient(app)

    def fake_chat(*, question, user_id="default", request_id=None):
        return {
            "answer": f"Echo {question}",
            "steps": [{"id": "1", "name": "supervisor", "status": "done"}],
            "question": question,
        }

    def fake_scan(*, symbol, user_id="default", threshold_pct=None, request_id=None):
        return {
            "symbol": symbol,
            "route": "normal",
            "steps": [{"id": "1", "name": "price_agent", "status": "done"}],
            "pending_events": [
                {"id": "scan-pend-1", "symbol": symbol, "gate": "gate1"}
            ],
            "gate1_action": "pending",
        }

    monkeypatch.setattr(ai_client, "ai_chat", fake_chat)
    monkeypatch.setattr("backend.main.ai_chat", fake_chat)
    monkeypatch.setattr(ai_client, "ai_scan", fake_scan)
    monkeypatch.setattr("backend.main.ai_scan", fake_scan)

    chat = client.post("/chat", json={"question": "Giá FPT?"})
    assert chat.status_code == 200
    body = chat.json()
    assert "FPT" in body["answer"]
    assert isinstance(body["steps"], list) and body["steps"]
    assert body["steps"][0]["name"] == "supervisor"
    assert "run_id" in body

    steps = client.get(f"/runs/{body['run_id']}/steps")
    assert steps.status_code == 200
    assert steps.json()["count"] == 1
    assert steps.json()["steps"][0]["id"] == "1"

    scan = client.post("/scan", json={"symbol": "FPT"})
    assert scan.status_code == 200
    assert scan.json()["symbol"] == "FPT"
    assert scan.json()["run_id"]
    assert client.get("/approvals").json()["count"] >= 1


def test_steps_one_shot_normalizes_and_get_endpoint(monkeypatch):
    """MVP one-shot: chat trả đủ steps; GET /runs/{id}/steps lấy lại."""
    client = TestClient(app)

    def fake_chat(*, question, user_id="default", request_id=None):
        return {
            "answer": "ok",
            "steps": [
                {"name": "rewrite_question"},  # thiếu id/status
                {"id": "2", "tool": "price_agent", "status": "done", "detail": "FPT"},
            ],
        }

    monkeypatch.setattr("backend.main.ai_chat", fake_chat)
    resp = client.post("/chat", json={"question": "Giá FPT?"})
    assert resp.status_code == 200
    data = resp.json()
    steps = data["steps"]
    assert steps[0]["id"] == "1"
    assert steps[0]["status"] == "done"
    assert steps[0]["name"] == "rewrite_question"
    assert steps[1]["name"] == "price_agent"
    assert steps[1]["detail"] == "FPT"

    got = client.get(f"/runs/{data['run_id']}/steps").json()
    assert got["steps"] == steps
    assert client.get("/runs/does-not-exist/steps").status_code == 404


def test_chat_empty_and_ai_down(monkeypatch):
    client = TestClient(app)
    assert client.post("/chat", json={"question": "  "}).status_code == 400

    def boom(**kwargs):
        raise ai_client.AiClientError("AI không kết nối được: refuse")

    monkeypatch.setattr("backend.main.ai_chat", boom)
    resp = client.post("/chat", json={"question": "Giá FPT?"})
    assert resp.status_code == 502
    assert "AI" in resp.json()["detail"]
