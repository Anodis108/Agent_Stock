"""Phase 4 — Timeline cập nhật theo steps từ Backend (không gọi AI)."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app

FE = Path(__file__).resolve().parents[1] / "frontend"


def test_frontend_timeline_uses_backend_steps_endpoints():
    js = (FE / "app.js").read_text(encoding="utf-8")
    assert "applyTimelineFromBackend" in js
    assert "showTimelineStart" in js
    assert "normalizeSteps" in js
    assert "/runs/" in js and "/steps" in js
    assert "8001" not in js
    assert "/v1/" not in js
    html = (FE / "index.html").read_text(encoding="utf-8")
    assert 'id="timeline-steps"' in html
    assert "GET /runs" in html or "/runs/" in html


def test_backend_run_steps_endpoint_feeds_timeline(monkeypatch):
    """Chat → run_id → GET /runs/{id}/steps có id/name/status (contract UI)."""
    client = TestClient(app)

    def fake_chat(*, question, user_id="default", request_id=None):
        return {
            "answer": "ok",
            "steps": [
                {"id": "1", "name": "rewrite_question", "status": "done"},
                {
                    "id": "2",
                    "name": "answer_composer",
                    "status": "done",
                    "detail": "FPT",
                },
            ],
        }

    monkeypatch.setattr("backend.main.ai_chat", fake_chat)
    chat = client.post("/chat", json={"question": "Giá FPT?"})
    assert chat.status_code == 200
    body = chat.json()
    assert body["steps"][0]["status"] == "done"
    run_id = body["run_id"]
    steps = client.get(f"/runs/{run_id}/steps").json()
    assert steps["count"] == 2
    assert steps["steps"][0]["name"] == "rewrite_question"
    assert steps["steps"][1]["detail"] == "FPT"
    for s in steps["steps"]:
        assert "id" in s and "name" in s and "status" in s
