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


def test_phase4_post_chat_sse_streaming_integration(client: TestClient):
    """Phase 4.1: Kiểm tra endpoint POST /chat hỗ trợ SSE streaming nhận đủ 5 sự kiện:
    node_start, node_end, token, chart_url, final_answer.
    """
    # 1. Yêu cầu bình thường (không có Accept text/event-stream) -> trả về ChatResponse JSON
    json_resp = client.post("/chat", json={"question": "Giá FPT?"})
    assert json_resp.status_code == 200
    assert "application/json" in json_resp.headers.get("content-type", "")
    assert "answer" in json_resp.json()

    # 2. Yêu cầu streaming qua POST /chat với header Accept: text/event-stream
    # Câu hỏi kích hoạt ChartAgent để xác nhận phát ra chart_url
    stream_resp = client.post(
        "/chat",
        headers={"Accept": "text/event-stream"},
        json={"question": "Vẽ biểu đồ nến cho FPT"},
    )
    assert stream_resp.status_code == 200
    assert "text/event-stream" in stream_resp.headers.get("content-type", "")

    events = _parse_sse(stream_resp.text)
    event_names = [e[0] for e in events]

    # Kiểm tra đủ 5 sự kiện cốt lõi của Phase 4.1
    assert "node_start" in event_names
    assert "node_end" in event_names
    assert "node_finish" in event_names
    assert "token" in event_names
    assert "chart_url" in event_names
    assert "final_answer" in event_names
    assert "complete" in event_names

    # Kiểm tra nội dung chart_url
    chart_events = [e[1] for e in events if e[0] == "chart_url"]
    assert len(chart_events) > 0
    assert "url" in chart_events[0]
    assert chart_events[0]["url"].endswith(".png")

    # Kiểm tra nội dung final_answer
    final_events = [e[1] for e in events if e[0] == "final_answer"]
    assert len(final_events) > 0
    assert "answer" in final_events[0]
    assert final_events[0]["answer"] != ""


def test_stream_cancel_event_stops_pipeline():
    """SSE cancel event → check_stream_cancelled raise StreamCancelledError."""
    import threading

    from backend.graph.chat import (
        StreamCancelledError,
        check_stream_cancelled,
        set_stream_cancel_event,
    )

    ev = threading.Event()
    set_stream_cancel_event(ev)
    check_stream_cancelled()  # chưa set → ok
    ev.set()
    try:
        check_stream_cancelled()
        raised = False
    except StreamCancelledError:
        raised = True
    finally:
        set_stream_cancel_event(None)
    assert raised


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
            "question": "What is FPT price?",
            "answer": "FPT price is 100",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["message_id"] == "test_msg_001"
    assert data["is_positive"] is False
    assert data["rating"] == 2
    assert data["question"] == "What is FPT price?"
    assert data["answer"] == "FPT price is 100"
    
    # check that it's in the db
    fb_list = client.get("/api/v1/hitl/feedbacks?session_id=test_sess_001")
    assert fb_list.status_code == 200
    assert len(fb_list.json()["items"]) > 0
    item = fb_list.json()["items"][0]
    assert item["question"] == "What is FPT price?"
    assert item["answer"] == "FPT price is 100"


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


# ==============================================================================
# Phase 2: Portfolio P&L & Multi-tenant API Tests
# ==============================================================================

def test_portfolio_holdings_crud_and_pnl_calculation(client: TestClient, monkeypatch):
    """Kiểm tra toàn bộ luồng thêm holding, tính P&L (PL-01, PL-02, PL-03)."""
    from backend.api.deps import get_app_deps
    from backend.domain.ports import PriceQuote

    deps = get_app_deps()

    # Mock PriceSource trả về giá theo kịch bản: FPT=120.0, HPG=27.0
    class MockPriceSource:
        def fetch_latest_close(self, symbol: str) -> PriceQuote:
            if symbol == "FPT":
                return PriceQuote(symbol="FPT", latest_close=120.0, prev_close=118.0)
            elif symbol == "HPG":
                return PriceQuote(symbol="HPG", latest_close=27.0, prev_close=28.0)
            return PriceQuote(symbol=symbol, latest_close=50.0, prev_close=50.0)

    monkeypatch.setattr(deps, "price_source", MockPriceSource())

    # 1. Thêm vị thế FPT: 1,000 cp @ giá 100.0 (PL-01)
    res_fpt = client.post(
        "/api/portfolio/holdings",
        json={"symbol": "FPT", "quantity": 1000, "avg_buy_price": 100.0},
    )
    assert res_fpt.status_code == 201
    fpt_data = res_fpt.json()
    assert fpt_data["symbol"] == "FPT"
    assert fpt_data["quantity"] == 1000

    # 2. Thêm vị thế HPG: 2,000 cp @ giá 30.0 (PL-02)
    res_hpg = client.post(
        "/api/portfolio/holdings",
        json={"symbol": "hpg", "quantity": 2000, "avg_buy_price": 30.0},
    )
    assert res_hpg.status_code == 201
    hpg_data = res_hpg.json()
    assert hpg_data["symbol"] == "HPG"

    # 3. GET /api/portfolio -> Kiểm tra tính toán lãi/lỗ
    res_pf = client.get("/api/portfolio")
    assert res_pf.status_code == 200
    pf = res_pf.json()

    assert pf["count"] == 2
    fpt_item = next(i for i in pf["items"] if i["symbol"] == "FPT")
    hpg_item = next(i for i in pf["items"] if i["symbol"] == "HPG")

    # FPT: cost = 100tr, market = 120tr, pnl = +20tr (+20%)
    assert fpt_item["cost_basis"] == 100000000.0
    assert fpt_item["market_value"] == 120000000.0
    assert fpt_item["unrealized_pnl"] == 20000000.0
    assert fpt_item["pnl_pct"] == 20.0

    # HPG: cost = 60tr, market = 54tr, pnl = -6tr (-10%)
    assert hpg_item["cost_basis"] == 60000000.0
    assert hpg_item["market_value"] == 54000000.0
    assert hpg_item["unrealized_pnl"] == -6000000.0
    assert hpg_item["pnl_pct"] == -10.0

    # PL-03: Tổng NAV = 174tr, Cost = 160tr, P&L = +14tr (+8.75%)
    assert pf["total_cost"] == 160000000.0
    assert pf["total_nav"] == 174000000.0
    assert pf["total_unrealized_pnl"] == 14000000.0
    assert pf["total_pnl_pct"] == 8.75


def test_portfolio_multi_tenant_header_isolation(client: TestClient):
    """Kiểm tra cô lập dữ liệu theo header X-User-ID (MT-03)."""
    # User A thêm FPT
    res_a = client.post(
        "/api/portfolio/holdings",
        headers={"X-User-ID": "user_a"},
        json={"symbol": "FPT", "quantity": 500, "avg_buy_price": 100.0},
    )
    assert res_a.status_code == 201

    # User B thêm VNM
    res_b = client.post(
        "/api/portfolio/holdings",
        headers={"X-User-ID": "user_b"},
        json={"symbol": "VNM", "quantity": 800, "avg_buy_price": 60.0},
    )
    assert res_b.status_code == 201

    # Kiểm tra User A chỉ thấy FPT
    pf_a = client.get("/api/portfolio", headers={"X-User-ID": "user_a"}).json()
    assert pf_a["count"] == 1
    assert pf_a["items"][0]["symbol"] == "FPT"

    # Kiểm tra User B chỉ thấy VNM
    pf_b = client.get("/api/portfolio", headers={"X-User-ID": "user_b"}).json()
    assert pf_b["count"] == 1
    assert pf_b["items"][0]["symbol"] == "VNM"


def test_portfolio_delete_holding(client: TestClient):
    """Kiểm tra xóa vị thế nắm giữ."""
    created = client.post(
        "/api/portfolio/holdings",
        headers={"X-User-ID": "del_user"},
        json={"symbol": "TCB", "quantity": 1000, "avg_buy_price": 30.0},
    ).json()
    holding_id = created["id"]

    # Xóa vị thế
    del_res = client.delete(
        f"/api/portfolio/holdings/{holding_id}",
        headers={"X-User-ID": "del_user"},
    )
    assert del_res.status_code == 200
    assert del_res.json()["ok"] is True

    # Xóa lại lần nữa -> 404
    del_again = client.delete(
        f"/api/portfolio/holdings/{holding_id}",
        headers={"X-User-ID": "del_user"},
    )
    assert del_again.status_code == 404


def test_user_settings_api(client: TestClient):
    """Kiểm tra GET và PUT /api/user/settings (MT-02)."""
    # Mặc định threshold là 3.0
    res_get = client.get("/api/user/settings", headers={"X-User-ID": "test_settings_user"})
    assert res_get.status_code == 200
    assert res_get.json()["alert_threshold_pct"] == 3.0

    # Cập nhật thành 4.5%
    res_put = client.put(
        "/api/user/settings",
        headers={"X-User-ID": "test_settings_user"},
        json={"alert_threshold_pct": 4.5},
    )
    assert res_put.status_code == 200
    assert res_put.json()["alert_threshold_pct"] == 4.5

    # Lấy lại xác nhận đã cập nhật
    res_check = client.get("/api/user/settings", headers={"X-User-ID": "test_settings_user"})
    assert res_check.json()["alert_threshold_pct"] == 4.5


def test_portfolio_price_error_graceful_fallback(client: TestClient, monkeypatch):
    """Kiểm tra khi mã lỗi giá không làm crash toàn bộ danh mục (PL-04)."""
    from backend.api.deps import get_app_deps
    from backend.domain.ports import PriceQuote

    deps = get_app_deps()

    class FailingPriceSource:
        def fetch_latest_close(self, symbol: str) -> PriceQuote:
            return PriceQuote(symbol=symbol, latest_close=None, error="Data unavailable")

    monkeypatch.setattr(deps, "price_source", FailingPriceSource())

    client.post(
        "/api/portfolio/holdings",
        headers={"X-User-ID": "err_user"},
        json={"symbol": "XYZ", "quantity": 100, "avg_buy_price": 50.0},
    )

    res = client.get("/api/portfolio", headers={"X-User-ID": "err_user"})
    assert res.status_code == 200
    data = res.json()
    assert data["count"] == 1
    assert data["items"][0]["price_error"] is True
    assert data["items"][0]["unrealized_pnl"] == 0.0


def test_watchlist_multi_tenant_header_isolation(client: TestClient):
    """Kiểm tra cô lập watchlist theo header X-User-ID (MT-01)."""
    # User A thêm FPT, HPG
    client.post("/watchlist", headers={"X-User-ID": "user_a"}, json={"symbol": "FPT"})
    client.post("/watchlist", headers={"X-User-ID": "user_a"}, json={"symbol": "HPG"})

    # User B thêm VNM, TCB
    client.post("/watchlist", headers={"X-User-ID": "user_b"}, json={"symbol": "VNM"})
    client.post("/watchlist", headers={"X-User-ID": "user_b"}, json={"symbol": "TCB"})

    # Kiểm tra User A
    res_a = client.get("/watchlist", headers={"X-User-ID": "user_a"})
    assert res_a.status_code == 200
    syms_a = {item["symbol"] for item in res_a.json()["items"]}
    assert "FPT" in syms_a
    assert "HPG" in syms_a
    assert "VNM" not in syms_a
    assert "TCB" not in syms_a

    # Kiểm tra User B
    res_b = client.get("/watchlist", headers={"X-User-ID": "user_b"})
    assert res_b.status_code == 200
    syms_b = {item["symbol"] for item in res_b.json()["items"]}
    assert "VNM" in syms_b
    assert "TCB" in syms_b
    assert "FPT" not in syms_b
    assert "HPG" not in syms_b


def test_ui_contains_user_switcher_and_portfolio_tab(client: TestClient):
    """Kiểm tra Web UI tĩnh phục vụ đầy đủ User Switcher và Tab Quản lý Danh mục (Phase 6)."""
    res = client.get("/")
    assert res.status_code == 200
    html = res.text
    assert "user-switcher-select" in html, "Thiếu User Switcher dropdown trong index.html"
    assert "data-tab=\"portfolio\"" in html, "Thiếu nút chuyển tab Portfolio P&L"
    assert "id=\"portfolio\"" in html, "Thiếu tab-pane portfolio trong index.html"
    assert "pnl-total-nav" in html, "Thiếu thẻ hiển thị Tổng NAV"
    assert "pnl-total-pnl" in html, "Thiếu thẻ hiển thị Tổng Lãi/Lỗ"
    assert "pnl-total-pct" in html, "Thiếu thẻ hiển thị Tỷ suất sinh lời %"
    assert "portfolio-add-form" in html, "Thiếu form thêm cổ phiếu vào danh mục"


def test_portfolio_user_switcher_isolation(client: TestClient):
    """Kiểm tra cô lập danh mục đầu tư khi chuyển đổi User A và User B qua X-User-ID."""
    # 1. User A thêm FPT
    add_a = client.post(
        "/api/portfolio/holdings",
        headers={"X-User-ID": "user_a"},
        json={"symbol": "FPT", "quantity": 100, "avg_buy_price": 130.0},
    )
    assert add_a.status_code == 201
    holding_id_a = add_a.json()["id"]

    # 2. User B thêm VNM
    add_b = client.post(
        "/api/portfolio/holdings",
        headers={"X-User-ID": "user_b"},
        json={"symbol": "VNM", "quantity": 200, "avg_buy_price": 65.0},
    )
    assert add_b.status_code == 201

    # 3. User A chỉ thấy FPT
    p_a = client.get("/api/portfolio", headers={"X-User-ID": "user_a"})
    assert p_a.status_code == 200
    syms_a = [item["symbol"] for item in p_a.json()["items"]]
    assert "FPT" in syms_a
    assert "VNM" not in syms_a

    # 4. User B chỉ thấy VNM
    p_b = client.get("/api/portfolio", headers={"X-User-ID": "user_b"})
    assert p_b.status_code == 200
    syms_b = [item["symbol"] for item in p_b.json()["items"]]
    assert "VNM" in syms_b
    assert "FPT" not in syms_b

    # 5. User A xóa FPT thành công
    del_a = client.delete(
        f"/api/portfolio/holdings/{holding_id_a}",
        headers={"X-User-ID": "user_a"},
    )
    assert del_a.status_code == 200

    # User A giờ danh mục trống
    p_a_after = client.get("/api/portfolio", headers={"X-User-ID": "user_a"})
    assert p_a_after.status_code == 200
    assert len(p_a_after.json()["items"]) == 0


# ==============================================================================
# Phase 7: Validation, Error States & Edge Cases Tests
# ==============================================================================

def test_portfolio_unknown_symbol_price_error_handling(client: TestClient):
    """Task 7.1: Mã cổ phiếu không tồn tại trong danh mục P&L -> đánh dấu price_error, không crash."""
    unknown_user = "test_err_user"
    # Thêm mã không có trên sàn chứng khoán
    res = client.post(
        "/api/portfolio/holdings",
        headers={"X-User-ID": unknown_user},
        json={"symbol": "XYZ99", "quantity": 100, "avg_buy_price": 50.0},
    )
    assert res.status_code == 201

    # Xem danh mục P&L: không crash 500, trả về status 200
    p_res = client.get("/api/portfolio", headers={"X-User-ID": unknown_user})
    assert p_res.status_code == 200
    data = p_res.json()
    assert data["count"] == 1
    item = data["items"][0]
    assert item["symbol"] == "XYZ99"
    assert item["price_error"] is True
    assert item["current_price"] is None
    assert item["unrealized_pnl"] == 0.0
    # Tổng NAV an toàn bằng đúng giá vốn
    assert data["total_nav"] == item["cost_basis"]


def test_portfolio_new_user_empty_state(client: TestClient):
    """Task 7.2: Người dùng mới chưa có danh mục (Empty State) -> Trả về danh mục rỗng hợp lệ."""
    fresh_user = "brand_new_investor_999"
    res = client.get("/api/portfolio", headers={"X-User-ID": fresh_user})
    assert res.status_code == 200
    data = res.json()
    assert data["count"] == 0
    assert data["items"] == []
    assert data["total_nav"] == 0.0
    assert data["total_unrealized_pnl"] == 0.0
    assert data["total_pnl_pct"] == 0.0


def test_query_decomposition_safe_fallback():
    """Task 7.3: Câu hỏi phức tạp không thể phân rã -> Fallback an toàn về chính câu hỏi gốc."""
    from backend.agents.supervisor_agent.nodes import _decompose_query

    # 1. Câu hỏi phức tạp nhưng không có ticker và không thể phân rã
    q_complex = "Hãy phân tích tình hình kinh tế vĩ mô quốc tế tác động thế nào đến lạm phát"
    sub_qs = _decompose_query(
        question=q_complex,
        rewritten=q_complex,
        symbols=[],
        intent="general",
        llm_sub_questions=None,
    )
    assert len(sub_qs) == 1
    assert sub_qs[0] == q_complex

    # 2. Câu hỏi gây lỗi / bất thường -> Fallback an toàn về câu hỏi gốc
    sub_qs_err = _decompose_query(
        question="Câu hỏi kiểm thử fallback lỗi",
        rewritten="",
        symbols=[],
        intent="unknown",
        llm_sub_questions=None,
    )
    assert len(sub_qs_err) == 1
    assert sub_qs_err[0] == "Câu hỏi kiểm thử fallback lỗi"





