"""Pydantic schemas for Web Approvals Review API."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from common.base.base_model import CustomBaseModel


class ApproveRequest(CustomBaseModel):
    approval_id: str | None = None
    user_id: str = "default"
    note: str | None = None


class RejectRequest(CustomBaseModel):
    approval_id: str | None = None
    reason: str = Field(default="", description="Lý do reject")
    user_id: str = "default"


class ReviewResponse(CustomBaseModel):
    ok: bool = True
    action: str = ""
    approval_id: str
    gate: str | None = None
    status: str | None = None
    error: str | None = None
    message: str = ""
    reviewed_at: str | None = None
    alert: dict[str, Any] | None = None
    watchlist_updates: list[dict[str, Any]] | None = None


class ApprovalsListResponse(CustomBaseModel):
    items: list[dict[str, Any]] = Field(default_factory=list)
    count: int = 0
