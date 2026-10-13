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
