"""Phase 5 — Stream/steps lỗi giữa chừng → timeline đánh error trên bước đó."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app, store
from backend.steps import ensure_steps_reflect_error, mark_mid_run_error, normalize_steps
from backend.store import WatchlistItem

FE = Path(__file__).resolve().parents[1] / "frontend"


def setup_function():
    store.clear()
    store.upsert_watchlist(WatchlistItem(symbol="FPT", threshold_pct=3.0))


def test_mark_mid_run_error_keeps_prior_done():
    steps = [
        {"id": "1", "name": "rewrite_question", "status": "done"},
        {"id": "2", "name": "price_agent", "status": "running"},
        {"id": "3", "name": "answer_composer", "status": "pending"},
    ]
    out = mark_mid_run_error(steps, detail="vnstock timeout")
    assert out[0]["status"] == "done"
    assert out[1]["status"] == "error"
    assert "timeout" in out[1]["detail"]
    assert out[2]["status"] == "pending"


def test_ensure_steps_reflect_error_from_payload_error():
    steps = [
        {"id": "1", "name": "rewrite_question", "status": "done"},
        {"id": "2", "name": "answer_composer", "status": "done"},
    ]
    out = ensure_steps_reflect_error(steps, error="composer failed")
    assert out[-1]["status"] == "error"
    assert "composer failed" in out[-1]["detail"]


def test_normalize_preserves_error_status():
    raw = [
        {"id": "1", "name": "price_agent", "status": "error", "detail": "x"},
        {"name": "news_agent"},  # default done
    ]
    out = normalize_steps(raw)
    assert out[0]["status"] == "error"
    assert out[1]["status"] == "done"


def test_backend_chat_preserves_mid_step_error(monkeypatch):
    client = TestClient(app)

    def fake_chat(*, question, user_id="default", request_id=None):
        return {
            "answer": "partial",
            "error": None,
            "steps": [
                {"id": "1", "name": "rewrite_question", "status": "done"},
                {
                    "id": "2",
                    "name": "price_agent",
                    "status": "error",
                    "detail": "price source down",
                },
                {"id": "3", "name": "answer_composer", "status": "done"},
            ],
        }

    monkeypatch.setattr("backend.main.ai_chat", fake_chat)
    resp = client.post("/chat", json={"question": "Giá FPT?"})
    assert resp.status_code == 200
    steps = resp.json()["steps"]
    assert steps[1]["status"] == "error"
    assert "price source" in steps[1]["detail"]
    # GET /runs/.../steps cùng contract
    run = client.get(f"/runs/{resp.json()['run_id']}/steps").json()
    assert run["steps"][1]["status"] == "error"


def test_backend_marks_error_when_ai_error_field_without_step_error(monkeypatch):
    client = TestClient(app)

    def fake_chat(*, question, user_id="default", request_id=None):
        return {
            "answer": "",
            "error": "llm crashed mid-compose",
            "steps": [
                {"id": "1", "name": "rewrite_question", "status": "done"},
                {"id": "2", "name": "answer_composer", "status": "done"},
            ],
        }

    monkeypatch.setattr("backend.main.ai_chat", fake_chat)
    body = client.post("/chat", json={"question": "Giá FPT?"}).json()
    assert any(s["status"] == "error" for s in body["steps"])


def test_frontend_marks_mid_run_error_on_timeline():
    js = (FE / "app.js").read_text(encoding="utf-8")
    assert "markTimelineMidError" in js
    assert 'status: "error"' in js or "status === \"error\"" in js
    assert "Bước lỗi" in js or "status === \"error\"" in js
