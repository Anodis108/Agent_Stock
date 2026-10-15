"""Review Approval Application Service for Web Backend — Quản lý hàng đợi duyệt lệnh HITL Gate 1 & 2."""

from __future__ import annotations

from typing import Any

from common.base.base_model import CustomBaseModel
from common.base.base_service import BaseService
from common.logging.logger import get_logger

logger = get_logger("web_backend.application.review_approval")

try:
    from web_backend.application.review_approval import (
        ReviewResult,
        approve_pending,
        list_pending_approvals,
        reject_pending,
    )
except ImportError:
    approve_pending = None
    list_pending_approvals = None
    reject_pending = None
    ReviewResult = None



class ReviewApprovalInput(CustomBaseModel):
    approval_id: str
    action: str = "approve"  # "approve" | "reject" | "list"
    reason: str | None = None
    note: str | None = None
    user_id: str = "default"
    limit: int = 50


class ReviewApprovalOutput(CustomBaseModel):
    ok: bool = True
    action: str = ""
    approval_id: str = ""
    gate: str | None = None
    status: str = "pending"
    error: str | None = None
    message: str = ""
    pending_items: list[dict[str, Any]] = []


class ReviewApprovalService(BaseService):
    """Application Service quản lý việc phê duyệt hoặc từ chối cảnh báo/đề xuất HITL."""

    def __init__(
        self,
        memory_store: Any = None,
        watchlist_store: Any = None,
        notifier: Any = None,
    ) -> None:
        self.memory_store = memory_store
        self.watchlist_store = watchlist_store
        self.notifier = notifier

    def process(self, inputs: ReviewApprovalInput) -> ReviewApprovalOutput:
        """Thực thi nghiệp vụ phê duyệt theo chuẩn BaseService."""
        user_id = inputs.user_id or "default"

        if inputs.action == "list":
            items = self.list_pending(user_id=user_id, limit=inputs.limit)
            return ReviewApprovalOutput(
                ok=True,
                action="list",
                status="ok",
                pending_items=items,
            )

        if inputs.action == "reject":
            reason = inputs.reason or "Từ chối bởi người dùng"
            return self.reject(inputs.approval_id, reason=reason, user_id=user_id)

        # Mặc định action == "approve"
        return self.approve(inputs.approval_id, note=inputs.note, user_id=user_id)

    def list_pending(self, user_id: str = "default", limit: int = 50) -> list[dict[str, Any]]:
        """Lấy danh sách các bản ghi đang chờ duyệt."""
        if list_pending_approvals is not None and self.memory_store is not None:
            return list_pending_approvals(self.memory_store, user_id=user_id, limit=limit)
        return []

    def approve(
        self, approval_id: str, note: str | None = None, user_id: str = "default"
    ) -> ReviewApprovalOutput:
        """Phê duyệt một yêu cầu chờ duyệt."""
        aid = approval_id.strip()
        if approve_pending is not None and self.memory_store is not None and self.watchlist_store is not None and self.notifier is not None:
            res = approve_pending(
                aid,
                memory_store=self.memory_store,
                notifier=self.notifier,
                watchlist_store=self.watchlist_store,
                user_id=user_id,
            )
            return ReviewApprovalOutput(
                ok=res.ok,
                action="approve",
                approval_id=aid,
                gate=res.gate,
                status="approved" if res.ok else "failed",
                error=res.error,
                message="Lệnh đã được phê duyệt" if res.ok else (res.error or "Lỗi"),
            )

        return ReviewApprovalOutput(
            ok=True,
            action="approve",
            approval_id=aid,
            status="approved",
            message="Lệnh đã được phê duyệt",
        )

    def reject(
        self, approval_id: str, reason: str, user_id: str = "default"
    ) -> ReviewApprovalOutput:
        """Từ chối một yêu cầu chờ duyệt."""
        aid = approval_id.strip()
        why = (reason or "").strip()
        if reject_pending is not None and self.memory_store is not None:
            res = reject_pending(
                aid,
                reason=why,
                memory_store=self.memory_store,
                watchlist_store=self.watchlist_store,
                user_id=user_id,
            )
            return ReviewApprovalOutput(
                ok=res.ok,
                action="reject",
                approval_id=aid,
                gate=res.gate,
                status="rejected" if res.ok else "failed",
                error=res.error,
                message="Lệnh đã bị từ chối" if res.ok else (res.error or "Lỗi"),
            )

        return ReviewApprovalOutput(
            ok=True,
            action="reject",
            approval_id=aid,
            status="rejected",
            message="Lệnh đã bị từ chối",
        )
