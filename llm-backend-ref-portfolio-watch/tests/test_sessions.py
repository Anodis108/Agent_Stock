"""Unit and integration tests for Session Management REST API.

Tests:
- GET /api/v1/sessions
- POST /api/v1/sessions
- GET /api/v1/sessions/{session_id}
- DELETE /api/v1/sessions/{session_id}
- Alias routes under /api/sessions
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.backend.main import app as product_app
from backend.database.connection import get_connection
from backend.database.repositories import MessageRepository, SessionRepository


@pytest.fixture
def client(tmp_path, monkeypatch):
    """TestClient wired to a temporary SQLite database."""
    temp_db = tmp_path / "test_sessions_api.db"
    monkeypatch.setenv("SQLITE_PATH", str(temp_db))
    # Ensure tables are initialized on the temp database
    conn = get_connection(temp_db)
    conn.close()
    return TestClient(product_app)


def test_create_and_list_sessions(client: TestClient):
    """Test creating sessions and listing them."""
    # Initially list might be empty
    res = client.get("/api/v1/sessions")
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert "count" in data

    # Create session 1 with custom title
    res1 = client.post("/api/v1/sessions", json={"title": "Nghiên cứu FPT & VNM"})
    assert res1.status_code == 201
    s1 = res1.json()
    assert s1["id"] is not None
    assert s1["title"] == "Nghiên cứu FPT & VNM"

    # Create session 2 with default title
    res2 = client.post("/api/v1/sessions", json={})
    assert res2.status_code == 201
    s2 = res2.json()
    assert s2["title"] == "Cuộc trò chuyện mới"

    # List sessions again
    res3 = client.get("/api/v1/sessions")
    assert res3.status_code == 200
    items = res3.json()["items"]
    ids = [item["id"] for item in items]
    assert s1["id"] in ids
    assert s2["id"] in ids


def test_get_session_detail_with_messages(client: TestClient, tmp_path):
    """Test retrieving session details including its message history."""
    # Create session
    res = client.post("/api/v1/sessions", json={"title": "Session with Messages"})
    assert res.status_code == 201
    session_id = res.json()["id"]

    # Directly insert messages into SQLite
    conn = get_connection()
    m_repo = MessageRepository(conn)
    m_repo.create(session_id=session_id, role="user", content="HPG có tin gì mới không?")
    m_repo.create(session_id=session_id, role="assistant", content="HPG vừa công bố sản lượng thép tháng 8 đạt kỷ lục.")
    conn.close()

    # Fetch detail
    detail_res = client.get(f"/api/v1/sessions/{session_id}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["session"]["id"] == session_id
    assert detail["message_count"] == 2
    assert len(detail["messages"]) == 2
    assert detail["messages"][0]["role"] == "user"
    assert detail["messages"][0]["content"] == "HPG có tin gì mới không?"
    assert detail["messages"][1]["role"] == "assistant"


def test_get_non_existent_session_returns_404(client: TestClient):
    """Verify 404 response for unknown session."""
    res = client.get("/api/v1/sessions/non-existent-session-id")
    assert res.status_code == 404
    assert "không tồn tại" in res.json()["detail"]


def test_delete_session_and_cascade(client: TestClient):
    """Test deleting a session."""
    # Create session
    res = client.post("/api/v1/sessions", json={"title": "Session to be deleted"})
    session_id = res.json()["id"]

    # Delete session
    del_res = client.delete(f"/api/v1/sessions/{session_id}")
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "deleted"

    # Confirm it's gone
    check_res = client.get(f"/api/v1/sessions/{session_id}")
    assert check_res.status_code == 404

    # Deleting again returns 404
    del_again = client.delete(f"/api/v1/sessions/{session_id}")
    assert del_again.status_code == 404


def test_alias_routes(client: TestClient):
    """Verify that /api/sessions alias routes work identically to /api/v1/sessions."""
    # Create via alias
    res = client.post("/api/sessions", json={"title": "Alias Session"})
    assert res.status_code == 201
    s_id = res.json()["id"]

    # Get via alias
    res_get = client.get(f"/api/sessions/{s_id}")
    assert res_get.status_code == 200
    assert res_get.json()["session"]["title"] == "Alias Session"

    # List via alias
    res_list = client.get("/api/sessions")
    assert res_list.status_code == 200
    assert any(s["id"] == s_id for s in res_list.json()["items"])

    # Delete via alias
    res_del = client.delete(f"/api/sessions/{s_id}")
    assert res_del.status_code == 200


def test_chat_creates_session_if_none_and_auto_titles(client: TestClient, monkeypatch):
    """POST /api/v1/chat creates a new session and auto-titles from first question."""
    monkeypatch.setattr(
        "backend.backend.main.ai_chat",
        lambda question, user_id, request_id: {
            "answer": "HPG là mã thép đầu ngành tại Việt Nam.",
            "route": "normal",
            "steps": [{"name": "price_agent", "status": "done"}],
        },
    )

    resp = client.post("/api/v1/chat", json={"question": "Phân tích mã cổ phiếu HPG"})
    assert resp.status_code == 200
    data = resp.json()
    assert "session_id" in data
    assert "message_id" in data
    session_id = data["session_id"]
    assert session_id is not None

    # Fetch session details from SQLite
    res_get = client.get(f"/api/v1/sessions/{session_id}")
    assert res_get.status_code == 200
    detail = res_get.json()
    assert detail["session"]["title"] == "Phân tích mã cổ phiếu HPG"
    assert detail["message_count"] == 2
    assert detail["messages"][0]["role"] == "user"
    assert detail["messages"][0]["content"] == "Phân tích mã cổ phiếu HPG"
    assert detail["messages"][1]["role"] == "assistant"
    assert detail["messages"][1]["content"] == "HPG là mã thép đầu ngành tại Việt Nam."


def test_chat_with_existing_default_session_updates_title(client: TestClient, monkeypatch):
    """POST /api/v1/chat with a default session updates its title from question."""
    # Create default session
    create_res = client.post("/api/v1/sessions", json={})
    assert create_res.status_code == 201
    session_id = create_res.json()["id"]
    assert create_res.json()["title"] == "Cuộc trò chuyện mới"

    monkeypatch.setattr(
        "backend.backend.main.ai_chat",
        lambda question, user_id, request_id: {
            "answer": "Vinamilk (VNM) duy trì biên lợi nhuận ổn định.",
            "route": "normal",
            "steps": [],
        },
    )

    resp = client.post(
        "/api/v1/chat",
        json={"session_id": session_id, "question": "Dự báo lợi nhuận VNM quý này"},
    )
    assert resp.status_code == 200
    assert resp.json()["session_id"] == session_id

    # Check that session title was updated from "Cuộc trò chuyện mới"
    res_get = client.get(f"/api/v1/sessions/{session_id}")
    assert res_get.status_code == 200
    detail = res_get.json()
    assert detail["session"]["title"] == "Dự báo lợi nhuận VNM quý này"
    assert detail["message_count"] == 2


def test_chat_with_custom_titled_session_keeps_title(client: TestClient, monkeypatch):
    """POST /api/v1/chat with custom-titled session preserves title and appends messages."""
    create_res = client.post("/api/v1/sessions", json={"title": "Chiến lược 2026"})
    assert create_res.status_code == 201
    session_id = create_res.json()["id"]

    monkeypatch.setattr(
        "backend.backend.main.ai_chat",
        lambda question, user_id, request_id: {
            "answer": f"Trả lời cho: {question}",
            "route": "normal",
            "steps": [],
        },
    )

    # First chat
    resp1 = client.post(
        "/api/v1/chat",
        json={"session_id": session_id, "question": "SSI có điểm mua không?"},
    )
    assert resp1.status_code == 200

    # Second chat
    resp2 = client.post(
        "/api/v1/chat",
        json={"session_id": session_id, "question": "Còn VND thì sao?"},
    )
    assert resp2.status_code == 200

    # Verify session retains its title and contains 4 messages
    res_get = client.get(f"/api/v1/sessions/{session_id}")
    assert res_get.status_code == 200
    detail = res_get.json()
    assert detail["session"]["title"] == "Chiến lược 2026"
    assert detail["message_count"] == 4
    roles = [m["role"] for m in detail["messages"]]
    assert roles == ["user", "assistant", "user", "assistant"]
