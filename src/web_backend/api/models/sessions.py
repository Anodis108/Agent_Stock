"""Pydantic schemas for Web Sessions & Messages API."""

from __future__ import annotations

from pydantic import Field

from common.base.base_model import CustomBaseModel


class SessionOut(CustomBaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str


class SessionListResponse(CustomBaseModel):
    items: list[SessionOut] = Field(default_factory=list)
    count: int = 0


class CreateSessionRequest(CustomBaseModel):
    title: str | None = Field(default="Cuộc trò chuyện mới", description="Tiêu đề phiên trò chuyện")


class MessageOut(CustomBaseModel):
    id: str
    session_id: str
    role: str
    content: str
    chart_path: str | None = None
    trace_data: str | None = None
    created_at: str


class SessionDetailResponse(CustomBaseModel):
    session: SessionOut
    messages: list[MessageOut] = Field(default_factory=list)
    message_count: int = 0
