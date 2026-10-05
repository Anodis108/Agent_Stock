"""GET/POST /approvals — HITL Gate 1 + Gate 2."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from backend.api.deps import AppDeps, get_app_deps
from backend.api.helpers.validation import normalize_approval_id
from backend.application.review_approval import (
    approve_pending,
    list_pending_approvals,
    reject_pending,
)

router = APIRouter(tags=["approvals"])


class ApproveRequest(BaseModel):
    user_id: str = "default"


class RejectRequest(BaseModel):
    reason: str = Field(description="Lý do reject")
    user_id: str = "default"


class ReviewResponse(BaseModel):
    ok: bool
    action: str
    approval_id: str
    gate: str | None = None
    error: str | None = None
    alert: dict[str, Any] | None = None
    watchlist_updates: list[dict[str, Any]] | None = None


class ApprovalsListResponse(BaseModel):
    items: list[dict[str, Any]] = Field(default_factory=list)
    count: int = 0


def _review_to_response(result) -> ReviewResponse:
    alert_payload = None
    if result.alert is not None:
        alert_payload = result.alert.model_dump(mode="json")
    updates = None
    if result.watchlist_updates:
        updates = [i.model_dump(mode="json") for i in result.watchlist_updates]
    return ReviewResponse(
        ok=result.ok,
        action=result.action,
        approval_id=result.approval_id,
        gate=result.gate,
        error=result.error,
        alert=alert_payload,
        watchlist_updates=updates,
    )


def _raise_if_failed(result) -> None:
    if result.ok:
        return
    err = (result.error or "không xử lý được").lower()
    if "rỗng" in err or "không hợp lệ" in err:
        raise HTTPException(status_code=400, detail=result.error)
    if "không tìm thấy" in err or "đã xử lý" in err:
        raise HTTPException(status_code=404, detail=result.error)
    raise HTTPException(status_code=400, detail=result.error)


@router.get("/approvals", response_model=ApprovalsListResponse)
def get_approvals(
    user_id: str = Query(default="default"),
    deps: AppDeps = Depends(get_app_deps),
) -> ApprovalsListResponse:
    items = list_pending_approvals(deps.memory_store, user_id=user_id)
    return ApprovalsListResponse(items=items, count=len(items))


@router.post("/approvals/{approval_id}/approve", response_model=ReviewResponse)
def post_approve(
    approval_id: str,
    body: ApproveRequest | None = None,
    deps: AppDeps = Depends(get_app_deps),
) -> ReviewResponse:
    aid = normalize_approval_id(approval_id)
    user_id = (body.user_id if body else "default") or "default"
    result = approve_pending(
        aid,
        memory_store=deps.memory_store,
        notifier=deps.notifier,
        watchlist_store=deps.watchlist_store,
        user_id=user_id,
    )
    _raise_if_failed(result)
    return _review_to_response(result)


@router.post("/approvals/{approval_id}/reject", response_model=ReviewResponse)
def post_reject(
    approval_id: str,
    body: RejectRequest,
    deps: AppDeps = Depends(get_app_deps),
) -> ReviewResponse:
    aid = normalize_approval_id(approval_id)
    # Để application ưu tiên "không tìm thấy" / "đã xử lý" trước "lý do rỗng"
    result = reject_pending(
        aid,
        body.reason or "",
        memory_store=deps.memory_store,
        watchlist_store=deps.watchlist_store,
        user_id=body.user_id or "default",
    )
    _raise_if_failed(result)
    return _review_to_response(result)
