"""Điểm 0–1 và nhãn nguồn cho tín hiệu feedback. Không gọi Langfuse."""

from __future__ import annotations

import sys

from fastapi.testclient import TestClient

from backend.api.routers.hitl import score_for_signal


def test_score_for_signal_maps_explicit_and_implicit():
    assert score_for_signal("copied") == (1.0, "implicit")
    assert score_for_signal("regenerated") == (0.0, "implicit")
    assert score_for_signal("abandoned") == (0.0, "implicit")
    assert score_for_signal("thumbs_up") == (1.0, "explicit")
    assert score_for_signal("thumbs_down") == (0.0, "explicit")
    assert score_for_signal("wrong_data") == (None, None)
    assert score_for_signal(None) == (None, None)


def test_api_stores_signal_score_and_source(client: TestClient, monkeypatch):
    calls: list[str] = []

    class _LangfuseBlocked:
        def __getattr__(self, name: str):
            calls.append(name)
            raise AssertionError(f"Langfuse was called: {name}")

    monkeypatch.setitem(sys.modules, "langfuse", _LangfuseBlocked())

    cases = [
        ("copied", 1.0, "implicit", True),
        ("regenerated", 0.0, "implicit", False),
        ("abandoned", 0.0, "implicit", False),
        ("thumbs_up", 1.0, "explicit", True),
        ("thumbs_down", 0.0, "explicit", False),
    ]
    for reason, score, source, positive in cases:
        resp = client.post(
            "/api/v1/hitl/feedback",
            json={
                "session_id": "signal-session",
                "message_id": f"msg-{reason}",
                "reason": reason,
                "feedback_text": reason,
                "is_positive": positive,
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["signal_score"] == score
        assert body["feedback_source"] == source
        assert 0.0 <= body["signal_score"] <= 1.0

    listed = client.get("/api/v1/hitl/feedbacks?session_id=signal-session")
    assert listed.status_code == 200
    items = {item["reason"]: item for item in listed.json()["items"]}
    assert items["copied"]["signal_score"] == 1.0
    assert items["copied"]["feedback_source"] == "implicit"
    assert items["regenerated"]["signal_score"] == 0.0
    assert items["abandoned"]["feedback_source"] == "implicit"
    assert items["thumbs_up"]["feedback_source"] == "explicit"
    assert calls == []


def test_thumbs_up_and_down_are_rows_in_postgres(client: TestClient):
    from backend.database.connection import get_connection
    from backend.database.pg import PgConn
    from backend.database.repositories import HITLEvaluationRepository

    for reason, positive in (("thumbs_up", True), ("thumbs_down", False)):
        resp = client.post(
            "/hitl/feedback",
            json={
                "session_id": "thumb-postgres",
                "message_id": f"msg-{reason}",
                "reason": reason,
                "is_positive": positive,
                "question": "RSI là gì",
                "answer": "RSI là chỉ báo",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["feedback_source"] == "explicit"

    conn = get_connection()
    try:
        assert isinstance(conn, PgConn)
        rows = {
            row.reason: row
            for row in HITLEvaluationRepository(conn).list_by_session("thumb-postgres")
        }
    finally:
        conn.close()
    assert rows["thumbs_up"].is_positive is True
    assert rows["thumbs_up"].signal_score == 1.0
    assert rows["thumbs_down"].is_positive is False
    assert rows["thumbs_down"].signal_score == 0.0


def test_web_entry_thumbs_still_write_postgres(tmp_path, monkeypatch):
    """Nút thích và không thích trên entry web ghi PostgreSQL."""
    from backend.main import app as web_app
    from backend.database.connection import get_connection
    from backend.database.pg import PgConn
    from backend.database.repositories import HITLEvaluationRepository

    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "thumbs.db"))
    monkeypatch.setenv("HITL_FEEDBACK_JSON_PATH", str(tmp_path / "hitl.json"))
    web = TestClient(web_app)
    for reason, positive in (("thumbs_up", True), ("thumbs_down", False)):
        resp = web.post(
            "/hitl/feedback",
            json={
                "session_id": "web-thumb",
                "message_id": f"msg-{reason}",
                "reason": reason,
                "is_positive": positive,
                "question": "RSI là gì",
                "answer": "RSI là chỉ báo",
            },
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["is_positive"] is positive

    conn = get_connection()
    try:
        assert isinstance(conn, PgConn)
        rows = {
            row.reason: row
            for row in HITLEvaluationRepository(conn).list_by_session("web-thumb")
        }
    finally:
        conn.close()
    assert rows["thumbs_up"].is_positive is True
    assert rows["thumbs_down"].is_positive is False
