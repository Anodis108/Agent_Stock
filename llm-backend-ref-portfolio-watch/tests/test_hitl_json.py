"""Tests for Phase 8: HITL Feedback telemetry export to resources/data/hitl_feedback.json."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory

import pytest
from fastapi.testclient import TestClient

from backend.backend.main import app
from backend.database.connection import get_connection, init_db
from backend.database.repositories import (
    HITLEvaluationRepository,
    MessageRepository,
    SessionRepository,
)
from backend.services.hitl_service import (
    get_hitl_feedback_json_path,
    record_hitl_telemetry,
)


@pytest.fixture
def temp_sqlite_and_json(monkeypatch):
    with TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        db_file = tmp_path / "test_pw.db"
        json_file = tmp_path / "hitl_feedback.json"

        monkeypatch.setenv("SQLITE_PATH", str(db_file))
        monkeypatch.setenv("HITL_FEEDBACK_JSON_PATH", str(json_file))

        conn = get_connection(db_file)
        yield conn, json_file
        conn.close()


def test_hitl_repository_with_reason(temp_sqlite_and_json):
    conn, _ = temp_sqlite_and_json
    s_repo = SessionRepository(conn)
    sess = s_repo.create("Phiên test")

    repo = HITLEvaluationRepository(conn)
    rec = repo.create(
        message_id="msg-123",
        session_id=sess.id,
        is_positive=False,
        rating=2,
        feedback="Số liệu giá không khớp",
        reason="Sai số liệu giá",
    )

    assert rec.id is not None
    assert rec.is_positive is False
    assert rec.rating == 2
    assert rec.feedback == "Số liệu giá không khớp"
    assert rec.reason == "Sai số liệu giá"

    fetched = repo.get(rec.id)
    assert fetched is not None
    assert fetched.reason == "Sai số liệu giá"

    listed = repo.list_by_session(sess.id)
    assert len(listed) == 1
    assert listed[0].reason == "Sai số liệu giá"


def test_hitl_telemetry_export_full_context(temp_sqlite_and_json):
    conn, json_file = temp_sqlite_and_json
    s_repo = SessionRepository(conn)
    m_repo = MessageRepository(conn)

    sess = s_repo.create("Phiên chat FPT")
    user_msg = m_repo.create(
        session_id=sess.id,
        role="user",
        content="Giá FPT hôm nay bao nhiêu?",
    )

    trace_dict = {
        "steps": [
            {"id": "rewrite", "name": "rewrite_question", "duration_s": 0.12},
            {"id": "price", "name": "price_agent", "duration_s": 0.35},
        ],
        "route": "price",
    }
    assistant_msg = m_repo.create(
        session_id=sess.id,
        role="assistant",
        content="Giá FPT hiện tại là 66.500 VND.",
        trace_data=json.dumps(trace_dict),
    )

    telemetry = record_hitl_telemetry(
        conn=conn,
        eval_id="eval-001",
        message_id=assistant_msg.id,
        session_id=sess.id,
        rating=1,
        is_positive=False,
        reason="Sai số liệu giá",
        user_feedback="Giá hôm nay phải là 120k",
    )

    assert telemetry["id"] == "eval-001"
    assert telemetry["session_id"] == sess.id
    assert telemetry["message_id"] == assistant_msg.id
    assert telemetry["question"] == "Giá FPT hôm nay bao nhiêu?"
    assert telemetry["answer"] == "Giá FPT hiện tại là 66.500 VND."
    assert telemetry["rating"] == 1
    assert telemetry["is_positive"] is False
    assert telemetry["reason"] == "Sai số liệu giá"
    assert telemetry["user_feedback"] == "Giá hôm nay phải là 120k"
    assert telemetry["execution_duration_s"] == 0.47
    assert telemetry["tokens_used"] is not None

    # Check JSON file on disk
    assert json_file.is_file()
    saved_list = json.loads(json_file.read_text(encoding="utf-8"))
    assert len(saved_list) == 1
    assert saved_list[0]["id"] == "eval-001"
    assert saved_list[0]["reason"] == "Sai số liệu giá"


def test_hitl_api_endpoint_with_telemetry(temp_sqlite_and_json):
    conn, json_file = temp_sqlite_and_json
    client = TestClient(app)

    s_repo = SessionRepository(conn)
    m_repo = MessageRepository(conn)
    sess = s_repo.create("Phiên test API")
    m_repo.create(session_id=sess.id, role="user", content="Tin tức VNM?")
    asst = m_repo.create(session_id=sess.id, role="assistant", content="Tin tức VNM xuất khẩu sữa...")

    payload = {
        "message_id": asst.id,
        "session_id": sess.id,
        "is_positive": False,
        "rating": 2,
        "reason": "Tin tức không đúng",
        "feedback_text": "Tin này từ tuần trước",
    }

    resp = client.post("/api/v1/hitl/feedback", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["reason"] == "Tin tức không đúng"
    assert data["rating"] == 2
    assert data["is_positive"] is False

    # Check alias route
    alias_resp = client.post("/hitl/feedback", json=payload)
    assert alias_resp.status_code == 200

    # Verify JSON file has been written
    assert json_file.is_file()
    content = json.loads(json_file.read_text(encoding="utf-8"))
    assert len(content) >= 1
    assert any(item["reason"] == "Tin tức không đúng" for item in content)
