"""Tests for real-time SSE streaming chat endpoint (/api/v1/chat/stream)."""

import json
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def _parse_sse_events(raw_text: str) -> list[tuple[str, dict]]:
    """Parse SSE string format into list of (event_name, data_dict)."""
    events = []
    current_event = None
    current_data = []

    for line in raw_text.splitlines():
        line = line.strip()
        if not line:
            if current_event and current_data:
                data_str = "\n".join(current_data)
                try:
                    data_obj = json.loads(data_str)
                except Exception:
                    data_obj = {"raw": data_str}
                events.append((current_event, data_obj))
            current_event = None
            current_data = []
            continue

        if line.startswith("event:"):
            current_event = line.split(":", 1)[1].strip()
        elif line.startswith("data:"):
            current_data.append(line.split(":", 1)[1].strip())

    if current_event and current_data:
        data_str = "\n".join(current_data)
        try:
            data_obj = json.loads(data_str)
        except Exception:
            data_obj = {"raw": data_str}
        events.append((current_event, data_obj))

    return events


def test_chat_stream_event_sequence_and_types():
    """Kiểm tra SSE endpoint phát đúng chuỗi event: node_start -> node_finish -> token -> complete."""
    response = client.post(
        "/api/v1/chat/stream",
        json={"question": "Giá cổ phiếu FPT hôm nay thế nào?", "user_id": "test_stream_user"},
    )
    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")

    events = _parse_sse_events(response.text)
    assert len(events) > 0

    event_names = [e[0] for e in events]
    assert "node_start" in event_names
    assert "node_finish" in event_names
    assert "token" in event_names
    assert "complete" in event_names

    # Kiểm tra payload node_start và node_finish
    starts = [e[1] for e in events if e[0] == "node_start"]
    finishes = [e[1] for e in events if e[0] == "node_finish"]
    assert any(s.get("node") == "pre_rewrite_guardrail" for s in starts)
    assert any("duration_s" in f and "duration_ms" in f for f in finishes)

    # Kiểm tra payload token
    tokens = [e[1] for e in events if e[0] == "token"]
    assert len(tokens) >= 1
    assert all("delta" in t for t in tokens)

    # Kiểm tra payload complete
    completes = [e[1] for e in events if e[0] == "complete"]
    assert len(completes) == 1
    comp = completes[0]
    assert "answer" in comp and comp["answer"]
    assert "total_duration_s" in comp
    assert "session_id" in comp and comp["session_id"]
    assert "message_id" in comp and comp["message_id"]
    assert "steps" in comp


def test_chat_stream_guardrail_refusal_streaming():
    """Kiểm tra câu hỏi out-of-scope phát refusal qua stream token và complete."""
    response = client.post(
        "/api/v1/chat/stream",
        json={"question": "Cho tôi giá cổ phiếu AAPL trên sàn Nasdaq?", "user_id": "test_stream_guardrail"},
    )
    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")

    events = _parse_sse_events(response.text)
    event_names = [e[0] for e in events]

    assert "node_start" in event_names
    assert "token" in event_names
    assert "complete" in event_names

    completes = [e[1] for e in events if e[0] == "complete"]
    assert len(completes) == 1
    comp = completes[0]
    assert "thị trường chứng khoán Việt Nam" in comp["answer"]
    assert "không hỗ trợ" in comp["answer"]


def test_chat_stream_backward_compatibility():
    """Kiểm tra endpoint thông thường POST /api/v1/chat vẫn hoạt động trả JSON bình thường."""
    response = client.post(
        "/api/v1/chat",
        json={"question": "Giá cổ phiếu VNM", "user_id": "test_stream_compat"},
    )
    assert response.status_code == 200
    assert "application/json" in response.headers.get("content-type", "")
    data = response.json()
    assert "answer" in data
    assert "steps" in data
    assert "session_id" in data
    assert "message_id" in data
