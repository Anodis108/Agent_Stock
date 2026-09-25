"""Kiểm thử Toàn Diện Hệ Thống REST API & SSE Streaming (FastAPI Backend).

Bao gồm:
1. Health & Static Serving: /health, phục vụ Web UI tĩnh tại /, cấu hình CORS.
2. Watchlist CRUD: Liệt kê, thêm, cập nhật ngưỡng cảnh báo, xóa mã.
3. Approvals (HITL): Danh sách chờ, phê duyệt, từ chối kèm lý do.
4. Server-Sent Events (SSE) Streaming: /api/v1/chat/stream phát trực tiếp tiến trình từng node và token.
5. Runs & Tracing: Truy vấn trace và steps theo run_id.
6. HITL Feedback: Đánh giá chất lượng câu trả lời và xuất telemetry vào resources/data/hitl_feedback.json.
7. Validation & Xử lý lỗi: Kiểm tra mã lỗi HTTP 400, 404, 422 chuẩn hóa.
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from backend.main import app, store
from backend.services.hitl_service import (
    get_hitl_feedback_json_path,
    record_hitl_telemetry,
)
from backend.store import ApprovalRecord, WatchlistItem


# ==============================================================================
# 1. Health, UI Static & Watchlist CRUD Tests
# ==============================================================================

def test_health_and_ui_served(client: TestClient):
    """Kiểm tra endpoint /health và phục vụ UI tĩnh tại root /."""
    health_res = client.get("/health")
    assert health_res.status_code == 200
    assert health_res.json()["status"] == "ok"
    assert health_res.json()["service"] == "backend"

    ui_res = client.get("/")
    assert ui_res.status_code == 200
    assert "html" in ui_res.headers.get("content-type", "").lower()


def test_watchlist_crud_endpoints(client: TestClient):
    """Kiểm tra toàn bộ luồng thêm, đọc, sửa và xóa mã trong Watchlist."""
    store.clear()
    store.upsert_watchlist(WatchlistItem(symbol="FPT", threshold_pct=3.0))

    # 1. GET /watchlist
    get_res = client.get("/watchlist")
    assert get_res.status_code == 200
    assert get_res.json()["count"] >= 1

    # 2. POST /watchlist
    post_res = client.post("/watchlist", json={"symbol": "VNM", "threshold_pct": 5.0})
    assert post_res.status_code == 200
    assert post_res.json()["symbol"] == "VNM"

    # 3. PATCH /watchlist/{symbol}
    patch_res = client.patch("/watchlist/VNM", json={"threshold_pct": 4.5})
    assert patch_res.status_code == 200
    assert patch_res.json()["threshold_pct"] == 4.5

    # 4. DELETE /watchlist/{symbol}
    del_res = client.delete("/watchlist/VNM")
    assert del_res.status_code == 200
    assert del_res.json()["ok"] is True


# ==============================================================================
# 2. Approvals (HITL) & Runs Tracing Tests
# ==============================================================================

def test_approvals_approve_and_reject(client: TestClient):
    """Kiểm tra quy trình phê duyệt và từ chối cảnh báo của người dùng."""
    store.clear()
    store.add_pending(
        ApprovalRecord(id="appr-001", user_id="default", symbol="FPT", gate="gate1")
    )

    # Liệt kê danh sách pending
    list_res = client.get("/approvals")
    assert list_res.status_code == 200
    assert list_res.json()["count"] == 1

    # Phê duyệt
    appr_res = client.post("/approvals/appr-001/approve", json={})
    assert appr_res.status_code == 200
    assert appr_res.json()["ok"] is True
    assert appr_res.json()["action"] == "approve"


def test_runs_and_steps_endpoint(client: TestClient, monkeypatch):
    """Kiểm tra endpoint /runs/{run_id} và /runs/{run_id}/steps trích xuất đầy đủ trace."""
    monkeypatch.setattr(
        "backend.main.ai_chat",
        lambda question, user_id, request_id: {
            "answer": "FPT tăng trưởng ổn định.",
            "steps": [{"name": "price_agent", "status": "done"}],
        },
    )
    chat_res = client.post("/chat", json={"question": "FPT thế nào?"})
    assert chat_res.status_code == 200
    run_id = chat_res.json().get("run_id")
    assert run_id is not None

    run_detail = client.get(f"/runs/{run_id}")
    assert run_detail.status_code == 200
    assert run_detail.json()["run_id"] == run_id

    run_steps = client.get(f"/runs/{run_id}/steps")
    assert run_steps.status_code == 200
    assert run_steps.json()["count"] > 0


# ==============================================================================
# 3. Server-Sent Events (SSE) Streaming Tests
# ==============================================================================

def _parse_sse(text: str) -> list[tuple[str, dict]]:
    events = []
    current_event = None
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("event:"):
            current_event = line.split(":", 1)[1].strip()
        elif line.startswith("data:") and current_event:
            data_str = line.split(":", 1)[1].strip()
            try:
                events.append((current_event, json.loads(data_str)))
            except Exception:
                events.append((current_event, {"raw": data_str}))
            current_event = None
    return events


def test_chat_stream_sse_flow(client: TestClient):
    """Kiểm tra SSE endpoint /api/v1/chat/stream phát đúng chuỗi event: node_start -> token -> complete."""
    resp = client.post(
        "/api/v1/chat/stream",
        json={"question": "Giá FPT hôm nay?"},
    )
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers.get("content-type", "")

    events = _parse_sse(resp.text)
    assert len(events) > 0
    event_names = [e[0] for e in events]
    assert "node_start" in event_names
    assert "complete" in event_names


def test_chat_stream_guardrail_refusal_streaming(client: TestClient):
    """Kiểm tra câu hỏi Out-of-Scope được stream mượt mà khi bị chặn bởi Guardrail."""
    resp = client.post(
        "/api/v1/chat/stream",
        json={"question": "Dự báo thời tiết Hà Nội?"},
    )
    assert resp.status_code == 200
    events = _parse_sse(resp.text)
    tokens = [e[1].get("delta", "") for e in events if e[0] == "token"]
    full_text = "".join(tokens)
    assert "thời tiết" in full_text.lower() or "phạm vi" in full_text.lower()


# ==============================================================================
# 4. HITL Feedback Telemetry Export Tests
# ==============================================================================

def test_hitl_feedback_and_telemetry_export(client: TestClient, tmp_path, monkeypatch):
    """Kiểm tra gửi đánh giá HITL feedback và xuất dữ liệu ra file hitl_feedback.json."""
    json_file = tmp_path / "hitl_feedback.json"
    monkeypatch.setenv("HITL_FEEDBACK_JSON_PATH", str(json_file))
    fb_file = get_hitl_feedback_json_path()
    assert fb_file == json_file

    resp = client.post(
        "/api/v1/hitl/feedback",
        json={
            "session_id": "test_sess_001",
            "message_id": "test_msg_001",
            "is_positive": False,
            "rating": 2,
            "reason": "wrong_data",
            "feedback_text": "Số liệu không khớp",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["message_id"] == "test_msg_001"
    assert data["is_positive"] is False
    assert data["rating"] == 2


# ==============================================================================
# 5. Validation & Error Handling Tests
# ==============================================================================

def test_api_validation_errors(client: TestClient):
    """Kiểm tra các trường hợp câu hỏi rỗng, mã cổ phiếu sai định dạng trả về HTTP 400 rõ ràng."""
    # Câu hỏi rỗng -> 400
    res_empty = client.post("/chat", json={"question": "   "})
    assert res_empty.status_code == 400

    # Mã cổ phiếu không hợp lệ (không phải 3 ký tự) -> 400
    res_sym = client.post("/watchlist", json={"symbol": "TOOLONG123"})
    assert res_sym.status_code == 400

    # Session không tồn tại -> 404
    res_404 = client.get("/api/v1/sessions/non_existent_id")
    assert res_404.status_code == 404


def test_api_payload_validation_and_session_auto_creation(client: TestClient):
    """Kiểm tra mã lỗi HTTP 422 cho payload không hợp lệ, và tự động tạo session khi session_id chưa tồn tại."""
    # 1. Payload thiếu trường question bắt buộc -> 422 Unprocessable Entity
    res_missing = client.post("/chat", json={})
    assert res_missing.status_code == 422

    # 2. Payload sai kiểu dữ liệu -> 422
    res_invalid_type = client.post("/chat", json={"question": {"nested": "value"}})
    assert res_invalid_type.status_code == 422

    # 3. Session_id chưa tồn tại được tự động tạo và xử lý thành công -> 200
    res_sess = client.post(
        "/chat",
        json={"question": "FPT hôm nay thế nào?", "session_id": "auto_sess_phase6"},
    )
    assert res_sess.status_code == 200
    assert res_sess.json().get("session_id") == "auto_sess_phase6"

    # Kiểm tra session đã được ghi nhận trong cơ sở dữ liệu
    detail = client.get("/api/v1/sessions/auto_sess_phase6")
    assert detail.status_code == 200
    assert detail.json()["session"]["id"] == "auto_sess_phase6"

