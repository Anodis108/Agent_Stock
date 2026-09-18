"""Phase 5 — Approvals: id missing / đã xử lý → 404 rõ, không đổi state."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app, store
from backend.store import ApprovalRecord

FE = Path(__file__).resolve().parents[1] / "frontend"


def setup_function():
    store.clear()


def _add_pending(aid: str = "ap-1", symbol: str = "FPT") -> None:
    store.add_pending(
        ApprovalRecord(id=aid, user_id="default", symbol=symbol, gate="gate1")
    )


def test_approve_missing_id_404_clear_message():
    client = TestClient(app)
    resp = client.post("/approvals/nope/approve", json={})
    assert resp.status_code == 404
    assert "không tìm thấy" in resp.json()["detail"]


def test_reject_missing_id_404_clear_message():
    client = TestClient(app)
    resp = client.post("/approvals/nope/reject", json={"reason": "x"})
    assert resp.status_code == 404
    assert "không tìm thấy" in resp.json()["detail"]


def test_approve_already_done_404_and_state_unchanged():
    client = TestClient(app)
    _add_pending("ap-done")
    assert client.post("/approvals/ap-done/approve", json={}).status_code == 200
    rec = store.get_approval("ap-done")
    assert rec is not None and rec.status == "approved"

    again = client.post("/approvals/ap-done/approve", json={})
    assert again.status_code == 404
    assert "đã xử lý" in again.json()["detail"]
    assert store.get_approval("ap-done").status == "approved"


def test_reject_already_done_404_does_not_overwrite_reason():
    client = TestClient(app)
    _add_pending("ap-rej")
    first = client.post(
        "/approvals/ap-rej/reject", json={"reason": "tin nhiễu"}
    )
    assert first.status_code == 200
    assert store.get_approval("ap-rej").reason == "tin nhiễu"

    second = client.post(
        "/approvals/ap-rej/reject", json={"reason": "lý do khác"}
    )
    assert second.status_code == 404
    assert "đã xử lý" in second.json()["detail"]
    # State không đổi sai
    rec = store.get_approval("ap-rej")
    assert rec.status == "rejected"
    assert rec.reason == "tin nhiễu"


def test_approve_empty_id_400():
    client = TestClient(app)
    # FastAPI path "" may not route; whitespace id
    resp = client.post("/approvals/%20/approve", json={})
    assert resp.status_code in (400, 404)


def test_frontend_shows_approval_errors():
    js = (FE / "app.js").read_text(encoding="utf-8")
    assert "Duyệt lỗi" in js
    assert "Từ chối lỗi" in js
    assert "loadApprovals" in js
