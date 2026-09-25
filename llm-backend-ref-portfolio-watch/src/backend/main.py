"""Portfolio Watch Backend — FastAPI Entrypoint Duy Nhất.

Hệ thống cung cấp:
- Giao diện API hỏi đáp chứng khoán Việt Nam qua mô hình AI Multi-Agent Swarm (LangGraph).
- Quản lý danh mục theo dõi (Watchlist) và phê duyệt Human-In-The-Loop (HITL) qua Store.
- Đồng bộ dữ liệu thị trường Market Watch 10D và lịch sử nến ngày.
- Streaming thời gian thực Server-Sent Events (SSE) `/api/v1/chat/stream` cho từng token và tiến trình agent.
- Phục vụ biểu đồ kỹ thuật tĩnh tại `/charts` và giao diện Web SPA tại `/`.
"""

from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from dotenv import find_dotenv, load_dotenv
from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.agents.chart_agent import get_charts_dir
from backend.ai_client import AiClientError, ai_chat, ai_scan
from backend.api.deps import AppDeps, get_app_deps
from backend.api.routers.chat import stream_chat_generator
from backend.api.routers.hitl import (
    alias_router as alias_hitl_router,
    direct_router as direct_hitl_router,
    router as hitl_router,
)
from backend.api.routers.market import (
    alias_router as alias_market_router,
    direct_router as direct_market_router,
    router as market_router,
)
from backend.api.routers.sessions import alias_router as alias_sessions_router
from backend.api.routers.sessions import router as sessions_router
from backend.cors_util import resolve_cors_origins
from backend.database.connection import get_connection
from backend.database.repositories import MessageRepository, SessionRepository
from backend.shared.logging import get_logger, setup_logging
from backend.shared.settings import settings
from backend.steps import ensure_steps_reflect_error, normalize_steps
from backend.store import (
    ApprovalRecord,
    LastQuoteRecord,
    RunRecord,
    Store,
    WatchlistItem,
)

load_dotenv(find_dotenv(".env"), override=False)
setup_logging(settings.log_level)
logger = get_logger(__name__)

# Thư mục giao diện Frontend Web SPA
_FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
if not _FRONTEND_DIR.is_dir():
    _FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "src" / "frontend"
if not _FRONTEND_DIR.is_dir():
    _FRONTEND_DIR = Path("/app/src/frontend")
if not _FRONTEND_DIR.is_dir():
    _FRONTEND_DIR = Path("/app/frontend")

DEFAULT_THRESHOLD = float(os.environ.get("DEFAULT_ALERT_THRESHOLD_PCT", "3.0"))
DEFAULT_WATCHLIST = [
    s.strip().upper()
    for s in os.environ.get("DEFAULT_WATCHLIST", "FPT,VNM,HPG").split(",")
    if s.strip()
]
_CORS_ORIGINS = resolve_cors_origins(os.environ.get("FRONTEND_ORIGIN"))
_SYMBOL_RE = re.compile(r"^[A-Za-z]{3}$")

# Khởi tạo Store quản lý Watchlist và Approvals
store = Store()
if not store.list_watchlist("default"):
    for sym in DEFAULT_WATCHLIST:
        store.upsert_watchlist(
            WatchlistItem(symbol=sym, threshold_pct=DEFAULT_THRESHOLD)
        )

# Khởi tạo FastAPI Application
app = FastAPI(title="Portfolio Watch Backend", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Đăng ký các router chuyên biệt
app.include_router(sessions_router)
app.include_router(alias_sessions_router)
app.include_router(market_router)
app.include_router(alias_market_router)
app.include_router(direct_market_router)
app.include_router(hitl_router)
app.include_router(alias_hitl_router)
app.include_router(direct_hitl_router)


# ==============================================================================
# Pydantic Schemas
# ==============================================================================

class WatchlistItemOut(BaseModel):
    """Schema xuất dữ liệu một mục trong Watchlist."""
    symbol: str
    threshold_pct: float
    user_id: str = "default"


class WatchlistListResponse(BaseModel):
    """Schema danh sách các mục trong Watchlist."""
    items: list[WatchlistItemOut] = Field(default_factory=list)
    count: int = 0


class CreateWatchlistRequest(BaseModel):
    """Schema yêu cầu thêm mã vào Watchlist."""
    symbol: str
    threshold_pct: float | None = None
    user_id: str = "default"


class UpdateWatchlistRequest(BaseModel):
    """Schema yêu cầu cập nhật ngưỡng cảnh báo của mã trong Watchlist."""
    threshold_pct: float
    user_id: str = "default"


class ChatRequest(BaseModel):
    """Schema yêu cầu trò chuyện từ người dùng."""
    question: str
    user_id: str = "default"
    session_id: str | None = None


class ScanRequest(BaseModel):
    """Schema yêu cầu quét giám sát bất thường của cổ phiếu."""
    symbol: str
    user_id: str = "default"
    threshold_pct: float | None = None


class ApproveRequest(BaseModel):
    """Schema yêu cầu phê duyệt hành động cảnh báo."""
    user_id: str = "default"


class RejectRequest(BaseModel):
    """Schema yêu cầu từ chối hành động cảnh báo kèm lý do."""
    reason: str
    user_id: str = "default"


MarketStatus = Literal["normal", "abnormal", "pending", "unknown"]


class MarketItemOut(BaseModel):
    """Schema xuất trạng thái một mã trên bảng Market Watch."""
    symbol: str
    price: float | None = None
    change_pct: float | None = None
    status: MarketStatus
    updated_at: str | None = None
    threshold_pct: float | None = None


class MarketListResponse(BaseModel):
    """Schema danh sách các mã trên bảng Market Watch."""
    items: list[MarketItemOut] = Field(default_factory=list)
    count: int = 0


# ==============================================================================
# Validation Helpers
# ==============================================================================

def _norm_symbol(raw: str) -> str:
    """Chuẩn hóa và kiểm tra mã cổ phiếu đúng định dạng 3 chữ cái."""
    sym = (raw or "").strip().upper()
    if not sym:
        raise HTTPException(status_code=400, detail="symbol rỗng")
    if not _SYMBOL_RE.match(sym):
        raise HTTPException(
            status_code=400,
            detail="symbol không hợp lệ (cần đúng 3 chữ cái)",
        )
    return sym


def _norm_threshold(value: float | None, *, required: bool = False) -> float | None:
    """Kiểm tra và chuẩn hóa ngưỡng cảnh báo (phải là số dương > 0)."""
    if value is None:
        if required:
            raise HTTPException(status_code=400, detail="threshold_pct bắt buộc")
        return None
    try:
        thr = float(value)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=400, detail="threshold_pct không hợp lệ"
        ) from exc
    if thr < 0:
        raise HTTPException(status_code=400, detail="ngưỡng không được âm")
    if thr == 0:
        raise HTTPException(status_code=400, detail="threshold_pct phải > 0")
    return thr


def _title_from_question(q: str, max_len: int = 40) -> str:
    """Trích xuất tiêu đề ngắn gọn cho session hội thoại từ câu hỏi đầu tiên."""
    cleaned = " ".join(q.strip().split())
    if len(cleaned) <= max_len:
        return cleaned
    return cleaned[:max_len].rstrip() + "..."


# ==============================================================================
# Health & Watchlist Endpoints
# ==============================================================================

@app.get("/health")
def health() -> dict[str, str]:
    """Kiểm tra trạng thái hoạt động của hệ thống backend."""
    return {"status": "ok", "service": "backend"}


@app.get("/watchlist", response_model=WatchlistListResponse)
def get_watchlist(user_id: str = Query(default="default")) -> WatchlistListResponse:
    """Lấy danh sách mã theo dõi trong danh mục của người dùng."""
    items = [
        WatchlistItemOut(
            symbol=i.symbol, threshold_pct=i.threshold_pct, user_id=i.user_id
        )
        for i in store.list_watchlist(user_id)
    ]
    return WatchlistListResponse(items=items, count=len(items))


@app.post("/watchlist", response_model=WatchlistItemOut)
def post_watchlist(body: CreateWatchlistRequest) -> WatchlistItemOut:
    """Thêm mã cổ phiếu mới vào danh mục theo dõi."""
    sym = _norm_symbol(body.symbol)
    thr = (
        _norm_threshold(body.threshold_pct)
        if body.threshold_pct is not None
        else DEFAULT_THRESHOLD
    )
    assert thr is not None
    saved = store.upsert_watchlist(
        WatchlistItem(
            symbol=sym, threshold_pct=float(thr), user_id=body.user_id or "default"
        )
    )
    return WatchlistItemOut(
        symbol=saved.symbol,
        threshold_pct=saved.threshold_pct,
        user_id=saved.user_id,
    )


@app.patch("/watchlist/{symbol}", response_model=WatchlistItemOut)
def patch_watchlist(symbol: str, body: UpdateWatchlistRequest) -> WatchlistItemOut:
    """Cập nhật ngưỡng cảnh báo biến động cho một mã trong danh mục."""
    sym = _norm_symbol(symbol)
    user_id = body.user_id or "default"
    existing = store.get_watchlist(user_id, sym)
    if existing is None:
        raise HTTPException(status_code=404, detail="không tìm thấy mã trong watchlist")
    thr = _norm_threshold(body.threshold_pct, required=True)
    assert thr is not None
    saved = store.upsert_watchlist(
        WatchlistItem(
            symbol=sym, threshold_pct=float(thr), user_id=user_id
        )
    )
    return WatchlistItemOut(
        symbol=saved.symbol,
        threshold_pct=saved.threshold_pct,
        user_id=saved.user_id,
    )


@app.delete("/watchlist/{symbol}")
def delete_watchlist(
    symbol: str, user_id: str = Query(default="default")
) -> dict[str, object]:
    """Xóa mã cổ phiếu khỏi danh mục theo dõi."""
    sym = _norm_symbol(symbol)
    if not store.delete_watchlist(user_id, sym):
        raise HTTPException(status_code=404, detail="không tìm thấy mã trong watchlist")
    return {"ok": True, "symbol": sym, "user_id": user_id}


# ==============================================================================
# Approvals (HITL) Endpoints
# ==============================================================================

@app.get("/approvals")
def get_approvals(user_id: str = Query(default="default")) -> dict[str, Any]:
    """Lấy danh sách các yêu cầu cảnh báo đang chờ người dùng phê duyệt."""
    items = [a.as_dict() for a in store.list_pending(user_id)]
    return {"items": items, "count": len(items)}


@app.post("/approvals/{approval_id}/approve")
def post_approve(
    approval_id: str, body: ApproveRequest | None = None
) -> dict[str, Any]:
    """Phê duyệt một yêu cầu cảnh báo từ hệ thống giám sát."""
    aid = (approval_id or "").strip()
    if not aid:
        raise HTTPException(status_code=400, detail="approval_id rỗng")
    user_id = (body.user_id if body else "default") or "default"
    before = store.get_approval(aid)
    before_status = before.status if before else None
    rec = store.approve(aid, user_id=user_id)
    if rec is None:
        after = store.get_approval(aid)
        after_status = after.status if after else None
        if before_status is not None and after_status != before_status:
            raise HTTPException(
                status_code=500, detail="approval state bị đổi ngoài ý muốn"
            )
        raise HTTPException(
            status_code=404, detail=store.explain_approval_failure(aid, user_id)
        )
    return {"ok": True, "action": "approve", "approval_id": rec.id, "item": rec.as_dict()}


@app.post("/approvals/{approval_id}/reject")
def post_reject(approval_id: str, body: RejectRequest) -> dict[str, Any]:
    """Từ chối một yêu cầu cảnh báo kèm lý do từ chối."""
    aid = (approval_id or "").strip()
    if not aid:
        raise HTTPException(status_code=400, detail="approval_id rỗng")
    if not (body.reason or "").strip():
        raise HTTPException(status_code=400, detail="reason rỗng")
    user_id = body.user_id or "default"
    before = store.get_approval(aid)
    before_status = before.status if before else None
    before_reason = before.reason if before else None
    rec = store.reject(aid, reason=body.reason.strip(), user_id=user_id)
    if rec is None:
        after = store.get_approval(aid)
        if before is not None and after is not None:
            if after.status != before_status or after.reason != before_reason:
                raise HTTPException(
                    status_code=500, detail="approval state bị đổi ngoài ý muốn"
                )
        raise HTTPException(
            status_code=404, detail=store.explain_approval_failure(aid, user_id)
        )
    return {"ok": True, "action": "reject", "approval_id": rec.id, "item": rec.as_dict()}


# ==============================================================================
# Market Status Endpoints
# ==============================================================================

def _market_status(
    symbol: str, route: str | None, pending_symbols: set[str]
) -> MarketStatus:
    if symbol.upper() in pending_symbols:
        return "pending"
    if not route:
        return "unknown"
    r = route.lower()
    if "bất thường" in r or "abnormal" in r:
        return "abnormal"
    if "bình thường" in r or "normal" in r:
        return "normal"
    return "unknown"


def _save_quote_from_scan(data: dict[str, Any], user_id: str) -> None:
    symbol = str(data.get("symbol") or "").strip().upper()
    if not symbol:
        return
    price_obj = data.get("price") if isinstance(data.get("price"), dict) else {}
    store.upsert_last_quote(
        LastQuoteRecord(
            symbol=symbol,
            user_id=user_id,
            price=price_obj.get("latest_close"),
            change_pct=price_obj.get("change_pct"),
            route=str(data.get("route") or ""),
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
    )


@app.get("/market", response_model=MarketListResponse)
def get_market(user_id: str = Query(default="default")) -> MarketListResponse:
    """Lấy danh sách mã thị trường kèm giá và trạng thái quét mới nhất."""
    pending_symbols = {a.symbol.upper() for a in store.list_pending(user_id)}
    items: list[MarketItemOut] = []
    for wl in store.list_watchlist(user_id):
        quote = store.get_last_quote(user_id, wl.symbol)
        route = quote.route if quote else None
        items.append(
            MarketItemOut(
                symbol=wl.symbol,
                price=quote.price if quote else None,
                change_pct=quote.change_pct if quote else None,
                status=_market_status(wl.symbol, route, pending_symbols),
                updated_at=quote.updated_at if quote else None,
                threshold_pct=wl.threshold_pct,
            )
        )
    return MarketListResponse(items=items, count=len(items))


# ==============================================================================
# Runs & Tracing Endpoints
# ==============================================================================

def _attach_run(
    *,
    kind: str,
    user_id: str,
    data: dict[str, Any],
) -> dict[str, Any]:
    """Gắn run_id và danh sách steps chuẩn hóa vào kết quả thực thi của chat/scan."""
    steps = ensure_steps_reflect_error(
        normalize_steps(data.get("steps")),
        error=data.get("error"),
    )
    run_id = str(uuid4())
    payload = dict(data)
    payload["steps"] = steps
    payload["run_id"] = run_id
    store.save_run(
        RunRecord(
            id=run_id,
            kind=kind,
            user_id=user_id,
            steps=steps,
            result=payload,
        )
    )
    return payload


@app.get("/runs/{run_id}")
def get_run(run_id: str) -> dict[str, Any]:
    """Lấy chi tiết kết quả và các bước xử lý (steps) của một lần chạy theo run_id."""
    run = store.get_run(run_id.strip())
    if run is None:
        raise HTTPException(status_code=404, detail="không tìm thấy run")
    return {
        "run_id": run.id,
        "kind": run.kind,
        "user_id": run.user_id,
        "steps": run.steps,
        "result": run.result,
        "answer": (run.result or {}).get("answer") if run.kind == "chat" else None,
    }


@app.get("/runs/{run_id}/steps")
def get_run_steps(run_id: str) -> dict[str, Any]:
    """Lấy danh sách steps chi tiết phục vụ hiển thị Timeline/Inspector."""
    run = store.get_run(run_id.strip())
    if run is None:
        raise HTTPException(status_code=404, detail="không tìm thấy run")
    return {
        "run_id": run.id,
        "kind": run.kind,
        "count": len(run.steps),
        "steps": run.steps,
    }


# ==============================================================================
# Chat & Scan Endpoints
# ==============================================================================

def _forward_chat_from_ai(data: dict[str, Any]) -> dict[str, Any]:
    """Đảm bảo trường `answer` luôn tồn tại dưới dạng chuỗi ở top-level."""
    out = dict(data or {})
    answer = out.get("answer")
    if answer is None or (isinstance(answer, str) and not answer.strip()):
        err = out.get("error")
        if err:
            out["answer"] = f"AI báo lỗi: {err}"
        else:
            out["answer"] = "(AI không trả lời — không có trường answer)"
    else:
        out["answer"] = str(answer)
    return out


@app.post("/chat")
@app.post("/api/v1/chat")
@app.post("/api/chat")
def post_chat(body: ChatRequest) -> dict[str, Any]:
    """Xử lý câu hỏi người dùng với AI Swarm qua SQLite session & message storage."""
    q = (body.question or "").strip()
    if not q:
        raise HTTPException(status_code=400, detail="câu hỏi rỗng")
    user_id = body.user_id or "default"
    request_id = str(uuid4())

    conn = get_connection()
    try:
        s_repo = SessionRepository(conn)
        m_repo = MessageRepository(conn)

        session_id = (body.session_id or "").strip()
        if session_id:
            session = s_repo.get(session_id)
            if session is None:
                session = s_repo.create(title=_title_from_question(q), session_id=session_id)
            elif session.title == "Cuộc trò chuyện mới":
                s_repo.update_title(session.id, _title_from_question(q))
            else:
                s_repo.touch(session.id)
        else:
            session = s_repo.create(title=_title_from_question(q))
            session_id = session.id

        m_repo.create(
            session_id=session_id,
            role="user",
            content=q,
        )

        try:
            data = ai_chat(question=q, user_id=user_id, request_id=request_id)
        except (AiClientError, Exception) as exc:
            raise HTTPException(status_code=502, detail=f"AI lỗi: {exc}") from exc

        forwarded = _forward_chat_from_ai(data)
        forwarded["request_id"] = request_id
        forwarded["session_id"] = session_id

        chart_path = forwarded.get("chart_path")
        trace_data = None
        if "steps" in forwarded or "route" in forwarded:
            import json
            trace_data = json.dumps({
                "steps": forwarded.get("steps", []),
                "route": forwarded.get("route", ""),
            }, ensure_ascii=False)

        assistant_msg = m_repo.create(
            session_id=session_id,
            role="assistant",
            content=forwarded.get("answer", ""),
            chart_path=chart_path,
            trace_data=trace_data,
        )
        forwarded["message_id"] = assistant_msg.id

        return _attach_run(kind="chat", user_id=user_id, data=forwarded)
    finally:
        conn.close()


@app.post("/chat/stream")
@app.post("/api/v1/chat/stream")
@app.post("/api/chat/stream")
def post_chat_stream(
    body: ChatRequest,
    deps: AppDeps = Depends(get_app_deps),
) -> StreamingResponse:
    """Endpoint Server-Sent Events (SSE) phát trực tiếp tiến trình từng agent và stream từng token của câu trả lời."""
    return StreamingResponse(
        stream_chat_generator(body, deps),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/scan")
def post_scan(body: ScanRequest) -> dict[str, Any]:
    """Quét và phân tích bất thường một mã cổ phiếu theo ngưỡng %."""
    sym = _norm_symbol(body.symbol)
    user_id = body.user_id or "default"
    thr = _norm_threshold(body.threshold_pct)
    request_id = str(uuid4())

    try:
        data = ai_scan(
            symbol=sym,
            user_id=user_id,
            threshold_pct=thr,
            request_id=request_id,
        )
    except (AiClientError, Exception) as exc:
        raise HTTPException(status_code=502, detail=f"AI lỗi: {exc}") from exc

    # Ghi nhận các sự kiện pending và cập nhật last quote
    pending = data.get("pending_events") or []
    if isinstance(pending, list):
        for ev in pending:
            if isinstance(ev, dict):
                aid = str(ev.get("id") or ev.get("approval_id") or uuid4())
                store.add_pending(
                    ApprovalRecord(
                        id=aid,
                        user_id=user_id,
                        symbol=str(ev.get("symbol") or data.get("symbol") or ""),
                        gate=str(ev.get("gate") or "gate1"),
                        payload=ev,
                    )
                )
    alert = data.get("alert")
    if isinstance(alert, dict) and data.get("gate1_action") == "pending":
        aid = str(alert.get("id") or alert.get("approval_id") or uuid4())
        store.add_pending(
            ApprovalRecord(
                id=aid,
                user_id=user_id,
                symbol=str(data.get("symbol") or ""),
                gate="gate1",
                payload=alert,
            )
        )

    _save_quote_from_scan(data, user_id)
    data = dict(data or {})
    data["request_id"] = request_id
    return _attach_run(kind="scan", user_id=user_id, data=data)


# ==============================================================================
# Static Mounts (Charts & Frontend SPA)
# ==============================================================================

_CHARTS_DIR = get_charts_dir()
_CHARTS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/charts", StaticFiles(directory=str(_CHARTS_DIR)), name="charts")

if _FRONTEND_DIR.is_dir():
    app.mount(
        "/",
        StaticFiles(directory=str(_FRONTEND_DIR), html=True),
        name="ui",
    )


if __name__ == "__main__":
    import uvicorn

    host = os.environ.get("API_HOST", settings.api_host or "127.0.0.1")
    port = int(os.environ.get("API_PORT", settings.api_port or 8000))
    uvicorn.run("backend.main:app", host=host, port=port, reload=False)
