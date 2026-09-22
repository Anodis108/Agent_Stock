"""Product entry (Phase 2) — một FastAPI: API + static UI; LangGraph qua ai_client."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any
from uuid import uuid4

from dotenv import find_dotenv, load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from src.portfolio_watch.backend.ai_client import AiClientError, ai_chat, ai_scan
from src.portfolio_watch.backend.cors_util import resolve_cors_origins
from src.portfolio_watch.backend.steps import ensure_steps_reflect_error, normalize_steps
from src.portfolio_watch.backend.store import ApprovalRecord, RunRecord, Store, WatchlistItem

load_dotenv(find_dotenv(".env"), override=False)

_FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

DEFAULT_THRESHOLD = float(os.environ.get("DEFAULT_ALERT_THRESHOLD_PCT", "3.0"))
DEFAULT_WATCHLIST = [
    s.strip().upper()
    for s in os.environ.get("DEFAULT_WATCHLIST", "FPT,VNM,HPG").split(",")
    if s.strip()
]
# CORS: FRONTEND_ORIGIN=http://127.0.0.1:5173 hoặc * (dev)
_CORS_ORIGINS = resolve_cors_origins(os.environ.get("FRONTEND_ORIGIN"))

_SYMBOL_RE = re.compile(r"^[A-Za-z]{3}$")
store = Store()
# Seed mặc định chỉ khi DB trống (giữ dữ liệu thật giữa lần chạy).
if not store.list_watchlist("default"):
    for sym in DEFAULT_WATCHLIST:
        store.upsert_watchlist(
            WatchlistItem(symbol=sym, threshold_pct=DEFAULT_THRESHOLD)
        )

app = FastAPI(title="Portfolio Watch Backend", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

class WatchlistItemOut(BaseModel):
    symbol: str
    threshold_pct: float
    user_id: str = "default"


class WatchlistListResponse(BaseModel):
    items: list[WatchlistItemOut] = Field(default_factory=list)
    count: int = 0


class CreateWatchlistRequest(BaseModel):
    symbol: str
    threshold_pct: float | None = None
    user_id: str = "default"


class UpdateWatchlistRequest(BaseModel):
    threshold_pct: float
    user_id: str = "default"


class ChatRequest(BaseModel):
    question: str
    user_id: str = "default"


class ScanRequest(BaseModel):
    symbol: str
    user_id: str = "default"
    threshold_pct: float | None = None


class ApproveRequest(BaseModel):
    user_id: str = "default"


class RejectRequest(BaseModel):
    reason: str
    user_id: str = "default"


def _norm_symbol(raw: str) -> str:
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
    """Ngưỡng % — từ chối âm / không hợp lệ (4xx rõ)."""
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


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "backend"}


@app.get("/watchlist", response_model=WatchlistListResponse)
def get_watchlist(user_id: str = Query(default="default")) -> WatchlistListResponse:
    items = [
        WatchlistItemOut(
            symbol=i.symbol, threshold_pct=i.threshold_pct, user_id=i.user_id
        )
        for i in store.list_watchlist(user_id)
    ]
    return WatchlistListResponse(items=items, count=len(items))


@app.post("/watchlist", response_model=WatchlistItemOut)
def post_watchlist(body: CreateWatchlistRequest) -> WatchlistItemOut:
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
    sym = _norm_symbol(symbol)
    if not store.delete_watchlist(user_id, sym):
        raise HTTPException(status_code=404, detail="không tìm thấy mã trong watchlist")
    return {"ok": True, "symbol": sym, "user_id": user_id}


@app.get("/approvals")
def get_approvals(user_id: str = Query(default="default")) -> dict[str, Any]:
    items = [a.as_dict() for a in store.list_pending(user_id)]
    return {"items": items, "count": len(items)}


@app.post("/approvals/{approval_id}/approve")
def post_approve(
    approval_id: str, body: ApproveRequest | None = None
) -> dict[str, Any]:
    aid = (approval_id or "").strip()
    if not aid:
        raise HTTPException(status_code=400, detail="approval_id rỗng")
    user_id = (body.user_id if body else "default") or "default"
    # Snapshot trước — nếu fail, status không đổi
    before = store.get_approval(aid)
    before_status = before.status if before else None
    rec = store.approve(aid, user_id=user_id)
    if rec is None:
        after = store.get_approval(aid)
        after_status = after.status if after else None
        if before_status is not None and after_status != before_status:
            # Không được xảy ra — bảo vệ state
            raise HTTPException(
                status_code=500, detail="approval state bị đổi ngoài ý muốn"
            )
        raise HTTPException(
            status_code=404, detail=store.explain_approval_failure(aid, user_id)
        )
    return {"ok": True, "action": "approve", "approval_id": rec.id, "item": rec.as_dict()}


@app.post("/approvals/{approval_id}/reject")
def post_reject(approval_id: str, body: RejectRequest) -> dict[str, Any]:
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


def _ingest_pending_from_scan(data: dict[str, Any], user_id: str) -> None:
    pending = data.get("pending_events") or []
    if not isinstance(pending, list):
        return
    for ev in pending:
        if not isinstance(ev, dict):
            continue
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


def _attach_run(
    *,
    kind: str,
    user_id: str,
    data: dict[str, Any],
) -> dict[str, Any]:
    """One-shot MVP: gắn run_id + steps[] chuẩn vào response chat/scan."""
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


def _forward_chat_from_ai(data: dict[str, Any]) -> dict[str, Any]:
    """Chuẩn hoá payload chat: giữ nguyên answer AI cho Frontend.

    FE chỉ đọc Backend — phải luôn có `answer` (string) ở top-level.
    """
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


@app.get("/runs/{run_id}")
def get_run(run_id: str) -> dict[str, Any]:
    """Lấy kết quả one-shot (answer/scan + steps) theo run_id."""
    run = store.get_run(run_id.strip())
    if run is None:
        raise HTTPException(status_code=404, detail="không tìm thấy run")
    return {
        "run_id": run.id,
        "kind": run.kind,
        "user_id": run.user_id,
        "steps": run.steps,
        "result": run.result,
        # Thuận FE: answer ở top-level nếu là chat
        "answer": (run.result or {}).get("answer") if run.kind == "chat" else None,
    }


@app.get("/runs/{run_id}/steps")
def get_run_steps(run_id: str) -> dict[str, Any]:
    """Endpoint trả đủ steps[] one-shot (không SSE — MVP Phase 3b)."""
    run = store.get_run(run_id.strip())
    if run is None:
        raise HTTPException(status_code=404, detail="không tìm thấy run")
    return {
        "run_id": run.id,
        "kind": run.kind,
        "count": len(run.steps),
        "steps": run.steps,
    }


@app.post("/chat")
def post_chat(body: ChatRequest) -> dict[str, Any]:
    q = (body.question or "").strip()
    if not q:
        raise HTTPException(status_code=400, detail="câu hỏi rỗng")
    user_id = body.user_id or "default"
    request_id = str(uuid4())
    try:
        data = ai_chat(question=q, user_id=user_id, request_id=request_id)
    except AiClientError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    forwarded = _forward_chat_from_ai(data)
    forwarded["request_id"] = request_id
    return _attach_run(kind="chat", user_id=user_id, data=forwarded)


@app.post("/scan")
def post_scan(body: ScanRequest) -> dict[str, Any]:
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
    except AiClientError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    _ingest_pending_from_scan(data, user_id)
    data = dict(data or {})
    data["request_id"] = request_id
    return _attach_run(kind="scan", user_id=user_id, data=data)


# Mount UI sau cùng — không che /health, /chat, …
if _FRONTEND_DIR.is_dir():
    app.mount(
        "/",
        StaticFiles(directory=str(_FRONTEND_DIR), html=True),
        name="ui",
    )


if __name__ == "__main__":
    import uvicorn

    host = os.environ.get("API_HOST", "127.0.0.1")
    port = int(os.environ.get("API_PORT", "8000"))
    uvicorn.run("src.portfolio_watch.backend.main:app", host=host, port=port, reload=False)
