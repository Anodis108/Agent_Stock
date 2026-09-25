"""Unit and integration tests for Human-In-The-Loop (HITL) Feedback REST API in Portfolio Watch V4.

Tests:
- POST /api/v1/hitl/feedback: Create feedback record in SQLite
- GET  /api/v1/hitl/feedbacks: List feedback records (with/without session_id filter)
- GET  /api/v1/hitl/feedback/{eval_id}: Detail query and 404 handling
- Alias routes: /api/hitl/feedback, /hitl/feedback, /api/hitl/feedbacks, /hitl/feedbacks
- Data persistence: Verify directly in SQLite hitl_evaluations table
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.backend.main import app as product_app
from backend.database.connection import get_connection
from backend.database.repositories import HITLEvaluationRepository


@pytest.fixture
def client_and_db(tmp_path, monkeypatch):
    """TestClient wired to an isolated temporary SQLite database."""
    temp_db = tmp_path / "test_hitl.db"
    monkeypatch.setenv("SQLITE_PATH", str(temp_db))
    conn = get_connection(temp_db)
    conn.close()
    return TestClient(product_app), temp_db


def test_post_hitl_feedback_positive(client_and_db):
    """POST /api/v1/hitl/feedback with positive rating and feedback text."""
    client, temp_db = client_and_db

    payload = {
        "message_id": "msg-101",
        "session_id": "ses-alpha",
        "is_positive": True,
        "rating": 5,
        "feedback_text": "Phân tích giá FPT rất chính xác và đầy đủ!",
    }
    resp = client.post("/api/v1/hitl/feedback", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert "id" in data
    assert data["message_id"] == "msg-101"
    assert data["session_id"] == "ses-alpha"
    assert data["is_positive"] is True
    assert data["rating"] == 5
    assert data["feedback_text"] == "Phân tích giá FPT rất chính xác và đầy đủ!"
    assert data["feedback"] == "Phân tích giá FPT rất chính xác và đầy đủ!"
    assert "created_at" in data

    # Verify directly in SQLite
    conn = get_connection(temp_db)
    try:
        repo = HITLEvaluationRepository(conn)
        rec = repo.get(data["id"])
        assert rec is not None
        assert rec.message_id == "msg-101"
        assert rec.session_id == "ses-alpha"
        assert rec.is_positive is True
        assert rec.rating == 5
        assert rec.feedback == "Phân tích giá FPT rất chính xác và đầy đủ!"
    finally:
        conn.close()


def test_post_hitl_feedback_negative_and_defaults(client_and_db):
    """POST /api/v1/hitl/feedback with negative feedback and default rating."""
    client, _ = client_and_db

    payload = {
        "message_id": "msg-102",
        "session_id": "ses-beta",
        "is_positive": False,
        "feedback_text": "Biểu đồ chưa thể hiện rõ đường trung bình động.",
    }
    resp = client.post("/api/v1/hitl/feedback", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["is_positive"] is False
    assert data["rating"] == 1  # Default for negative feedback
    assert data["feedback_text"] == "Biểu đồ chưa thể hiện rõ đường trung bình động."


def test_get_hitl_feedbacks_list_and_filter(client_and_db):
    """GET /api/v1/hitl/feedbacks list and session_id filtering."""
    client, _ = client_and_db

    # Create 3 feedbacks across 2 sessions
    client.post(
        "/api/v1/hitl/feedback",
        json={"message_id": "m1", "session_id": "s-1", "is_positive": True, "rating": 5},
    )
    client.post(
        "/api/v1/hitl/feedback",
        json={"message_id": "m2", "session_id": "s-1", "is_positive": False, "rating": 2},
    )
    client.post(
        "/api/v1/hitl/feedback",
        json={"message_id": "m3", "session_id": "s-2", "is_positive": True, "rating": 4},
    )

    # List all
    resp_all = client.get("/api/v1/hitl/feedbacks")
    assert resp_all.status_code == 200
    data_all = resp_all.json()
    assert data_all["count"] == 3
    assert len(data_all["items"]) == 3

    # Filter by session_id s-1
    resp_s1 = client.get("/api/v1/hitl/feedbacks?session_id=s-1")
    assert resp_s1.status_code == 200
    data_s1 = resp_s1.json()
    assert data_s1["count"] == 2
    assert all(item["session_id"] == "s-1" for item in data_s1["items"])

    # Filter by session_id s-2
    resp_s2 = client.get("/api/v1/hitl/feedbacks?session_id=s-2")
    assert resp_s2.status_code == 200
    data_s2 = resp_s2.json()
    assert data_s2["count"] == 1
    assert data_s2["items"][0]["message_id"] == "m3"


def test_get_hitl_feedback_detail_and_404(client_and_db):
    """GET /api/v1/hitl/feedback/{eval_id} detail and not-found behavior."""
    client, _ = client_and_db

    create_resp = client.post(
        "/api/v1/hitl/feedback",
        json={"message_id": "m-detail", "session_id": "s-detail", "rating": 4, "is_positive": True},
    )
    eval_id = create_resp.json()["id"]

    # Valid get
    get_resp = client.get(f"/api/v1/hitl/feedback/{eval_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == eval_id

    # Non-existent ID -> 404
    err_resp = client.get("/api/v1/hitl/feedback/non-existent-uuid-12345")
    assert err_resp.status_code == 404


def test_hitl_alias_routes(client_and_db):
    """Verify alias routes /api/hitl/* and /hitl/*."""
    client, _ = client_and_db

    # Alias /api/hitl/feedback
    resp1 = client.post(
        "/api/hitl/feedback",
        json={"message_id": "m-alias1", "session_id": "s-alias", "rating": 5, "is_positive": True},
    )
    assert resp1.status_code == 200
    id1 = resp1.json()["id"]

    # Alias /hitl/feedback
    resp2 = client.post(
        "/hitl/feedback",
        json={"message_id": "m-alias2", "session_id": "s-alias", "rating": 4, "is_positive": True},
    )
    assert resp2.status_code == 200

    # Alias /api/hitl/feedbacks
    resp_list1 = client.get("/api/hitl/feedbacks")
    assert resp_list1.status_code == 200
    assert resp_list1.json()["count"] >= 2

    # Alias /hitl/feedbacks
    resp_list2 = client.get("/hitl/feedbacks")
    assert resp_list2.status_code == 200
    assert resp_list2.json()["count"] >= 2

    # Alias /hitl/feedback/{id}
    detail = client.get(f"/hitl/feedback/{id1}")
    assert detail.status_code == 200
    assert detail.json()["id"] == id1
