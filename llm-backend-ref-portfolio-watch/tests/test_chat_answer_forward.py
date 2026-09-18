"""Phase 4 — Chat: Backend forward AI answer → Frontend nhận câu trả lời cuối."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from backend import ai_client
from backend.main import app, _forward_chat_from_ai

FE = Path(__file__).resolve().parents[1] / "frontend"


def test_forward_chat_preserves_ai_answer():
    out = _forward_chat_from_ai(
        {"answer": "FPT đóng cửa 100.", "steps": [], "symbol": "FPT"}
    )
    assert out["answer"] == "FPT đóng cửa 100."
    assert out["symbol"] == "FPT"


def test_forward_chat_fills_answer_when_ai_omits():
    out = _forward_chat_from_ai({"error": "timeout", "steps": []})
    assert "timeout" in out["answer"]
    empty = _forward_chat_from_ai({"steps": []})
    assert "answer" in empty and empty["answer"]


def test_backend_chat_forwards_ai_answer_to_client(monkeypatch):
    """test-plan §3: curl chat qua Backend nhận answer (+ steps)."""
    client = TestClient(app)

    def fake_chat(*, question, user_id="default", request_id=None):
        return {
            "answer": f"Giá FPT hôm nay ổn. (q={question})",
            "symbol": "FPT",
            "steps": [
                {"id": "1", "name": "rewrite_question", "status": "done"},
                {"id": "2", "name": "answer_composer", "status": "done"},
            ],
            "question": question,
            "hitl_used": False,
        }

    monkeypatch.setattr(ai_client, "ai_chat", fake_chat)
    monkeypatch.setattr("backend.main.ai_chat", fake_chat)

    resp = client.post("/chat", json={"question": "Giá FPT?"})
    assert resp.status_code == 200
    body = resp.json()
    assert "Giá FPT hôm nay ổn" in body["answer"]
    assert body["symbol"] == "FPT"
    assert body["run_id"]
    # FE có thể lấy lại answer qua run
    run = client.get(f"/runs/{body['run_id']}")
    assert run.status_code == 200
    assert "Giá FPT hôm nay ổn" in (run.json().get("answer") or "")


def test_frontend_reads_final_answer_from_backend_response():
    """FE production path đọc data.answer — không gọi AI thẳng."""
    js = (FE / "app.js").read_text(encoding="utf-8")
    assert "extractFinalAnswer" in js
    assert "data.answer" in js
    assert 'api("POST", "/chat"' in js or "/chat" in js
    assert "8001" not in js
    assert "/v1/chat" not in js
