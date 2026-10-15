"""Pydantic schemas for Web HITL (Feedback & Approvals) API."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from common.base.base_model import CustomBaseModel


class FeedbackCreateRequest(CustomBaseModel):
    message_id: str | None = None
    session_id: str | None = None
    is_positive: bool = True
    rating: int | None = Field(default=None, ge=1, le=5)
    feedback_text: str | None = None
    feedback: str | None = None
    reason: str | None = None
    question: str | None = None
    answer: str | None = None
    user_id: str = "default"
    trace_data: str | None = None


class FeedbackOut(CustomBaseModel):
    id: str
    message_id: str | None = None
    session_id: str | None = None
    rating: int | None = None
    feedback: str | None = None
    feedback_text: str | None = None
    is_positive: bool = True
    reason: str | None = None
    question: str | None = None
    answer: str | None = None
    signal_score: float | None = None
    feedback_source: str | None = None
    created_at: str


class FeedbackListResponse(CustomBaseModel):
    items: list[FeedbackOut] = Field(default_factory=list)
    count: int = 0
