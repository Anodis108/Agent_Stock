"""Test presentation layer of web_backend (helpers, models, routers)."""

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from web_backend.api.helpers.exception_handler import register_exception_handlers
from web_backend.api.helpers.middlewares import CorrelationIdMiddleware, register_middlewares
from web_backend.api.helpers.validation import (
    normalize_approval_id,
    normalize_question,
    normalize_reject_reason,
    normalize_symbol,
    title_from_question,
    validate_threshold_pct,
)
from web_backend.api.models.approvals import ApproveRequest, RejectRequest, ReviewResponse
from web_backend.api.models.chat import ChatRequest, ChatResponse, ChatStep
from web_backend.api.models.hitl import FeedbackCreateRequest, FeedbackOut
from web_backend.api.models.market import MarketMatrixItemOut, MarketSessionOut
from web_backend.api.models.portfolio import CreateHoldingRequest, HoldingOut, UserSettingsOut
from web_backend.api.models.scan import ScanRequest, ScanResponse
from web_backend.api.models.sessions import CreateSessionRequest, MessageOut, SessionOut
from web_backend.api.models.watchlist import CreateWatchlistRequest, WatchlistItemOut
from web_backend.api.routers import (
    approvals,
    chat,
    hitl,
    market,
    portfolio,
    scan,
    sessions,
    watchlist,
)


def test_validation_normalize_symbol():
    assert normalize_symbol("fpt") == "FPT"
    assert normalize_symbol("  vnm  ") == "VNM"
    assert normalize_symbol("E1VFVN30") == "E1VFVN30"

    with pytest.raises(HTTPException) as exc:
        normalize_symbol("")
    assert exc.value.status_code == 400

    with pytest.raises(HTTPException) as exc:
        normalize_symbol("TOOLONGTICKERNAME")
    assert exc.value.status_code == 400


def test_validation_normalize_question():
    assert normalize_question("   Hôm nay FPT thế nào?   ") == "Hôm nay FPT thế nào?"

    with pytest.raises(HTTPException) as exc:
        normalize_question("   ")
    assert exc.value.status_code == 400


def test_validation_title_from_question():
    q = "Phân tích kỹ thuật mã cổ phiếu FPT trong phiên hôm nay"
    title = title_from_question(q, max_len=20)
    assert len(title) <= 23  # with ellipsis
    assert title.endswith("...")


def test_validation_threshold_pct():
    assert validate_threshold_pct(5.5) == 5.5
    assert validate_threshold_pct("3.0") == 3.0
    assert validate_threshold_pct(None) is None

    with pytest.raises(HTTPException) as exc:
        validate_threshold_pct(None, required=True)
    assert exc.value.status_code == 400

    with pytest.raises(HTTPException) as exc:
        validate_threshold_pct(-1.0)
    assert exc.value.status_code == 400


def test_validation_approval_helpers():
    assert normalize_approval_id("  APP-123  ") == "APP-123"
    with pytest.raises(HTTPException) as exc:
        normalize_approval_id("")
    assert exc.value.status_code == 400

    assert normalize_reject_reason("  Giá quá cao  ") == "Giá quá cao"
    with pytest.raises(HTTPException) as exc:
        normalize_reject_reason("")
    assert exc.value.status_code == 400


def test_pydantic_models_instantiation():
    chat_req = ChatRequest(question="Giá FPT?")
    assert chat_req.question == "Giá FPT?"
    assert chat_req.user_id == "default"

    holding_req = CreateHoldingRequest(symbol="FPT", quantity=100, buy_price=120.5)
    assert holding_req.symbol == "FPT"
    assert holding_req.quantity == 100

    session_req = CreateSessionRequest(title="Tư vấn đầu tư")
    assert session_req.title == "Tư vấn đầu tư"

    wl_req = CreateWatchlistRequest(symbol="HPG", alert_threshold_pct=5.0)
    assert wl_req.symbol == "HPG"
    assert wl_req.alert_threshold_pct == 5.0

    fb_req = FeedbackCreateRequest(reason="thumbs_up", is_positive=True)
    assert fb_req.reason == "thumbs_up"
    assert fb_req.is_positive is True


def test_all_routers_included_in_test_app():
    app = FastAPI()
    app.include_router(chat.router)
    app.include_router(portfolio.router)
    app.include_router(watchlist.router)
    app.include_router(sessions.router)
    app.include_router(hitl.router)
    app.include_router(market.router)
    app.include_router(approvals.router)
    app.include_router(scan.router)

    client = TestClient(app)

    # Market sessions test
    resp = client.get("/api/market/sessions")
    assert resp.status_code == 200
    assert len(resp.json()) > 0
    assert resp.json()[0]["session_type"] == "ATO"


def test_correlation_id_middleware():
    app = FastAPI()
    register_middlewares(app)

    @app.get("/ping")
    def ping():
        return {"ping": "pong"}

    client = TestClient(app)
    # Gửi kèm header
    resp = client.get("/ping", headers={"X-Correlation-ID": "custom-trace-id"})
    assert resp.status_code == 200
    assert resp.headers.get("X-Correlation-ID") == "custom-trace-id"

    # Không gửi header, middleware tự sinh
    resp2 = client.get("/ping")
    assert resp2.status_code == 200
    assert "X-Correlation-ID" in resp2.headers
    assert len(resp2.headers["X-Correlation-ID"]) > 0


def test_exception_handler_middleware():
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/trigger-400")
    def trigger_400():
        raise HTTPException(status_code=400, detail="Mã lỗi thử nghiệm 400")

    client = TestClient(app)
    resp = client.get("/trigger-400")
    assert resp.status_code == 400
    assert resp.json() == {"detail": "Mã lỗi thử nghiệm 400"}


def test_approvals_router_endpoints():
    app = FastAPI()
    app.include_router(approvals.router)
    client = TestClient(app)

    # List approvals
    resp = client.get("/approvals")
    assert resp.status_code == 200
    assert "items" in resp.json()

    # Approve non-existent action -> 404
    resp = client.post("/approvals/APP-NON-EXISTENT/approve")
    assert resp.status_code == 404

    # Reject non-existent action -> 404
    resp = client.post("/approvals/APP-NON-EXISTENT/reject", json={"reason": "Giá quá cao"})
    assert resp.status_code == 404


def test_watchlist_router_endpoints():
    app = FastAPI()
    app.include_router(watchlist.router)
    client = TestClient(app)

    resp = client.get("/watchlist")
    assert resp.status_code == 200
    assert "items" in resp.json()


def test_scan_router_endpoint():
    app = FastAPI()
    app.include_router(scan.router)
    client = TestClient(app)

    resp = client.post("/api/v1/scan", json={"symbols": ["FPT", "VNM"], "threshold_pct": 3.0})
    assert resp.status_code == 200
    assert "alerts" in resp.json()

