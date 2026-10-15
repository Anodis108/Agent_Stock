"""Unit & integration tests for AI Backend Presentation Layer (src/ai_backend/api/)."""

from __future__ import annotations

import json
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from ai_backend.api.helpers.exception_handler import register_ai_exception_handlers
from ai_backend.api.helpers.middlewares import (
    CorrelationIdMiddleware,
    RequestLoggingMiddleware,
)
from ai_backend.api.models.scan_models import ScanAlertOut, ScanRequest, ScanResponse
from ai_backend.api.models.stream_models import (
    ChatStreamRequest,
    CompleteEvent,
    ErrorEvent,
    HoldingSnapshot,
    NodeFinish,
    NodeStart,
    TokenEvent,
    WatchlistSnapshot,
)
from ai_backend.api.routers.chat_stream import (
    alias_router as chat_stream_alias_router,
    router as chat_stream_router,
)
from ai_backend.api.routers.health import router as health_router
from ai_backend.api.routers.scan import (
    alias_router as scan_alias_router,
    router as scan_router,
)


@pytest.fixture
def ai_test_app() -> FastAPI:
    """Khởi tạo FastAPI test app đăng ký đầy đủ router và middleware của AI Backend."""
    app = FastAPI(title="AI Backend Test App")
    app.add_middleware(CorrelationIdMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    register_ai_exception_handlers(app)

    app.include_router(health_router)
    app.include_router(chat_stream_router)
    app.include_router(chat_stream_alias_router)
    app.include_router(scan_router)
    app.include_router(scan_alias_router)

    @app.get("/test-error")
    def trigger_error():
        raise HTTPException(status_code=400, detail="Lỗi thử nghiệm AI")

    return app


@pytest.fixture
def client(ai_test_app: FastAPI) -> TestClient:
    return TestClient(ai_test_app)


def test_stream_and_scan_models_instantiation():
    """Kiểm tra khởi tạo và tuần tự hóa các model Pydantic kế thừa CustomBaseModel."""
    # 1. Snapshots
    wl = WatchlistSnapshot(symbol="FPT", threshold_pct=4.0, user_id="user_a")
    assert wl.symbol == "FPT"
    assert wl.threshold_pct == 4.0

    hd = HoldingSnapshot(symbol="HPG", quantity=500, avg_buy_price=28.5)
    assert hd.symbol == "HPG"
    assert hd.quantity == 500

    # 2. ChatStreamRequest
    req = ChatStreamRequest(
        question="Xu hướng cổ phiếu VNM?",
        user_id="user_b",
        request_id="req-123",
        watchlist=[wl],
        holdings=[hd],
    )
    assert req.question == "Xu hướng cổ phiếu VNM?"
    assert len(req.watchlist or []) == 1

    # 3. Stream Events
    n_start = NodeStart(node="supervisor", input_data={"q": "test"})
    assert n_start.event == "node_start"
    assert n_start.node == "supervisor"

    n_finish = NodeFinish(node="supervisor", output_data={"route": "market"}, duration_ms=120)
    assert n_finish.event == "node_finish"
    assert n_finish.duration_ms == 120

    tok = TokenEvent(token="Xin chào", index=0)
    assert tok.event == "token"
    assert tok.token == "Xin chào"

    comp = CompleteEvent(answer="Đạt mục tiêu", route="market", request_id="req-123")
    assert comp.event == "complete"
    assert comp.answer == "Đạt mục tiêu"

    err = ErrorEvent(error="Timeout", request_id="req-123")
    assert err.event == "error"

    # 4. Scan models
    scan_req = ScanRequest(symbol="MWG", threshold_pct=2.5)
    assert scan_req.symbol == "MWG"

    scan_res = ScanResponse(
        symbol="MWG",
        route="technical",
        alerts=[ScanAlertOut(symbol="MWG", route="technical", threshold_pct=2.5, triggered=True)],
    )
    assert scan_res.symbol == "MWG"
    assert len(scan_res.alerts) == 1


def test_health_endpoint(client: TestClient):
    """Kiểm tra endpoint GET /health của AI Backend."""
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["service"] == "ai_backend"
    assert data["port"] == 8001
    assert data["swarm"] == "ready"


def test_chat_stream_sse_endpoint(client: TestClient):
    """Kiểm tra endpoint POST /v1/chat/stream phát luồng Server-Sent Events."""
    req_body = {
        "question": "Phân tích giá cổ phiếu FPT",
        "user_id": "test_user",
        "request_id": "req-stream-001",
    }
    resp = client.post("/v1/chat/stream", json=req_body)
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers.get("content-type", "").lower()

    lines = resp.text.split("\n")
    events = [line.replace("event: ", "").strip() for line in lines if line.startswith("event: ")]
    assert "node_start" in events
    assert "token" in events
    assert "complete" in events or "node_finish" in events


def test_scan_endpoint(client: TestClient):
    """Kiểm tra endpoint POST /v1/scan trả về phân tích kỹ thuật."""
    req_body = {
        "symbol": "FPT",
        "threshold_pct": 3.0,
        "user_id": "test_user",
        "request_id": "req-scan-001",
    }
    resp = client.post("/v1/scan", json=req_body)
    assert resp.status_code == 200
    data = resp.json()
    assert data["symbol"] == "FPT"
    assert "route" in data
    assert "alerts" in data or "steps" in data


def test_correlation_id_middleware(client: TestClient):
    """Kiểm tra CorrelationIdMiddleware gắn và trả lại header X-Correlation-ID."""
    # Gửi có header
    resp = client.get("/health", headers={"X-Correlation-ID": "custom-ai-cid-123"})
    assert resp.status_code == 200
    assert resp.headers.get("x-correlation-id") == "custom-ai-cid-123"

    # Gửi không có header (tự động sinh mới)
    resp2 = client.get("/health")
    assert resp2.status_code == 200
    assert resp2.headers.get("x-correlation-id") is not None
    assert len(resp2.headers.get("x-correlation-id", "")) > 0


def test_exception_handler_middleware(client: TestClient):
    """Kiểm tra global exception handlers trả về định dạng JSON chuẩn kèm tag service: ai_backend."""
    # 1. 400 Custom HTTPException
    resp = client.get("/test-error")
    assert resp.status_code == 400
    data = resp.json()
    assert data["service"] == "ai_backend"
    assert "Lỗi thử nghiệm AI" in data["error"]

    # 2. 422 RequestValidationError
    resp_val = client.post("/v1/scan", json={"symbol": 12345, "threshold_pct": "not_a_float"})
    assert resp_val.status_code == 422
    data_val = resp_val.json()
    assert data_val["service"] == "ai_backend"
    assert data_val["status_code"] == 422
    assert "details" in data_val
