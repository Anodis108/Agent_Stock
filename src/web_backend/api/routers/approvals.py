"""HITL Approvals Review Router for Web Backend."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from web_backend.api.deps import AppDeps, get_app_deps, get_current_user_id
from web_backend.api.helpers.validation import (
    normalize_approval_id,
    normalize_reject_reason,
)
from web_backend.api.models.approvals import (
    ApproveRequest,
    ApprovalsListResponse,
    RejectRequest,
    ReviewResponse,
)

router = APIRouter(tags=["approvals"])

try:
    from web_backend.application.review_approval import (
        approve_pending,
        list_pending_approvals,
        reject_pending,
    )
except ImportError:
    approve_pending = None
    list_pending_approvals = None
    reject_pending = None



def _review_to_response(result) -> ReviewResponse:
    alert_payload = None
    if getattr(result, "alert", None) is not None:
        alert_payload = result.alert.model_dump(mode="json") if hasattr(result.alert, "model_dump") else dict(result.alert)
    updates = None
    if getattr(result, "watchlist_updates", None):
        updates = [i.model_dump(mode="json") if hasattr(i, "model_dump") else dict(i) for i in result.watchlist_updates]
    return ReviewResponse(
        ok=getattr(result, "ok", True),
        action=getattr(result, "action", ""),
        approval_id=getattr(result, "approval_id", ""),
        gate=getattr(result, "gate", None),
        status="approved" if getattr(result, "action", "") == "approve" else "rejected",
        error=getattr(result, "error", None),
        alert=alert_payload,
        watchlist_updates=updates,
    )


def _raise_if_failed(result) -> None:
    if getattr(result, "ok", True):
        return
    err = (getattr(result, "error", "") or "không xử lý được").lower()
    if "rỗng" in err or "không hợp lệ" in err:
        raise HTTPException(status_code=400, detail=result.error)
    if "không tìm thấy" in err or "đã xử lý" in err:
        raise HTTPException(status_code=404, detail=result.error)
    raise HTTPException(status_code=400, detail=result.error)


@router.get("/api/v1/approvals", response_model=ApprovalsListResponse)
@router.get("/api/approvals", response_model=ApprovalsListResponse)
@router.get("/approvals", response_model=ApprovalsListResponse)
def get_approvals(
    user_id: str = Depends(get_current_user_id),
    deps: AppDeps = Depends(get_app_deps),
) -> ApprovalsListResponse:
    if list_pending_approvals is not None and hasattr(deps, "memory_store") and deps.memory_store is not None:
        items = list_pending_approvals(deps.memory_store, user_id=user_id)
        return ApprovalsListResponse(items=items, count=len(items))
    return ApprovalsListResponse(items=[], count=0)


@router.post("/api/v1/approvals/{approval_id}/approve", response_model=ReviewResponse)
@router.post("/api/approvals/{approval_id}/approve", response_model=ReviewResponse)
@router.post("/approvals/{approval_id}/approve", response_model=ReviewResponse)
def post_approve(
    approval_id: str,
    body: ApproveRequest | None = None,
    current_user: str = Depends(get_current_user_id),
    deps: AppDeps = Depends(get_app_deps),
) -> ReviewResponse:
    aid = normalize_approval_id(approval_id)
    user_id = (body.user_id if body and body.user_id != "default" else current_user) or "default"
    if approve_pending is not None:
        result = approve_pending(
            aid,
            memory_store=getattr(deps, "memory_store", None),
            notifier=getattr(deps, "notifier", None),
            watchlist_store=getattr(deps, "watchlist_store", None),
            user_id=user_id,
        )
        _raise_if_failed(result)
        return _review_to_response(result)

    raise HTTPException(status_code=404, detail="không tìm thấy bản ghi chờ duyệt")


@router.post("/api/v1/approvals/{approval_id}/reject", response_model=ReviewResponse)
@router.post("/api/approvals/{approval_id}/reject", response_model=ReviewResponse)
@router.post("/approvals/{approval_id}/reject", response_model=ReviewResponse)
def post_reject(
    approval_id: str,
    body: RejectRequest,
    current_user: str = Depends(get_current_user_id),
    deps: AppDeps = Depends(get_app_deps),
) -> ReviewResponse:
    aid = normalize_approval_id(approval_id)
    reason = normalize_reject_reason(body.reason)
    user_id = (body.user_id if body.user_id != "default" else current_user) or "default"

    if reject_pending is not None:
        result = reject_pending(
            aid,
            reason=reason,
            memory_store=getattr(deps, "memory_store", None),
            watchlist_store=getattr(deps, "watchlist_store", None),
            user_id=user_id,
        )
        _raise_if_failed(result)
        return _review_to_response(result)

    raise HTTPException(status_code=404, detail="không tìm thấy bản ghi chờ duyệt")


@router.post("/approvals/review", response_model=ReviewResponse)
@router.post("/api/v1/approvals/review", response_model=ReviewResponse)
def review_approval(
    req: ApproveRequest | RejectRequest,
    deps: AppDeps = Depends(get_app_deps),
) -> ReviewResponse:
    aid = normalize_approval_id(req.approval_id)
    is_reject = isinstance(req, RejectRequest)
    if is_reject:
        return post_reject(aid, req, deps=deps)
    else:
        return post_approve(aid, req, deps=deps)
