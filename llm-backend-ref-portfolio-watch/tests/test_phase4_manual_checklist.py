"""Phase 4 — Kiểm thử tay (tự động hoá cùng luồng FE→Backend).

Checklist:
  1) Hỏi 1 câu → thấy steps + câu trả lời cuối
  2) Thêm mã → quét
  3) Duyệt nếu có cảnh báo chờ
"""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app, store
from backend.store import WatchlistItem

FE = Path(__file__).resolve().parents[1] / "frontend"


def setup_function():
    store.clear()
    store.upsert_watchlist(WatchlistItem(symbol="FPT", threshold_pct=3.0))


def test_phase4_manual_checklist_via_backend(monkeypatch):
    """Cùng endpoint mà frontend/app.js gọi — không cần browser."""
    client = TestClient(app)

    def fake_chat(*, question, user_id="default", request_id=None):
        return {
            "answer": f"FPT đóng cửa 100.0. (trả lời cho: {question})",
            "symbol": "FPT",
            "steps": [
                {"id": "1", "name": "rewrite_question", "status": "done"},
                {"id": "2", "name": "price_agent", "status": "done"},
                {"id": "3", "name": "answer_composer", "status": "done"},
            ],
        }

    def fake_scan(*, symbol, user_id="default", threshold_pct=None, request_id=None):
        return {
            "symbol": symbol,
            "route": "abnormal",
            "steps": [
                {"id": "1", "name": "price_agent", "status": "done"},
                {"id": "2", "name": "event_classifier", "status": "done"},
            ],
            "pending_events": [
                {
                    "id": f"pend-{symbol}",
                    "symbol": symbol,
                    "gate": "gate1",
                }
            ],
            "gate1_action": "pending",
        }

    monkeypatch.setattr("backend.main.ai_chat", fake_chat)
    monkeypatch.setattr("backend.main.ai_scan", fake_scan)

    # 1) Hỏi 1 câu → steps + answer
    chat = client.post("/chat", json={"question": "Giá FPT hôm nay?"})
    assert chat.status_code == 200
    body = chat.json()
    assert "FPT" in body["answer"]
    assert isinstance(body["steps"], list) and len(body["steps"]) >= 2
    assert all("status" in s and "name" in s for s in body["steps"])
    assert body["run_id"]
    steps = client.get(f"/runs/{body['run_id']}/steps").json()
    assert steps["count"] == len(body["steps"])

    # 2) Thêm mã → quét
    add = client.post(
        "/watchlist", json={"symbol": "HPG", "threshold_pct": 1.0}
    )
    assert add.status_code == 200
    assert add.json()["symbol"] == "HPG"
    wl = client.get("/watchlist").json()
    assert any(i["symbol"] == "HPG" for i in wl["items"])

    scan = client.post("/scan", json={"symbol": "HPG", "threshold_pct": 1.0})
    assert scan.status_code == 200
    assert scan.json()["symbol"] == "HPG"
    assert scan.json()["steps"]

    # 3) Duyệt nếu có pending
    pending = client.get("/approvals").json()
    assert pending["count"] >= 1
    aid = pending["items"][0]["id"]
    ok = client.post(f"/approvals/{aid}/approve", json={})
    assert ok.status_code == 200
    assert ok.json()["ok"] is True
    assert client.get("/approvals").json()["count"] == 0


def test_frontend_supports_manual_checklist_actions():
    """UI có đủ control cho checklist tay."""
    html = (FE / "index.html").read_text(encoding="utf-8")
    js = (FE / "app.js").read_text(encoding="utf-8")
    assert 'id="chat-form"' in html
    assert 'id="timeline-steps"' in html
    assert 'id="watchlist-form"' in html
    assert 'id="scan-form"' in html or "doScan" in js
    assert 'id="approvals-list"' in html
    assert 'api("POST", "/chat"' in js or "/chat" in js
    assert "/scan" in js and "/watchlist" in js and "approve" in js
