"""Pydantic schemas for Web Chat API."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from common.base.base_model import CustomBaseModel


class ChatRequest(CustomBaseModel):
    question: str = Field(description="Câu hỏi tự do của người dùng")
    user_id: str = Field(default="default", description="Mã định danh người dùng")
    session_id: str | None = Field(default=None, description="Mã phiên đối thoại (nếu có)")


class ChatStep(CustomBaseModel):
    id: str
    name: str
    status: str = "done"
    detail: str | None = None
    input: Any = None
    output: Any = None
    static_info: Any = None
    system_prompt: Any = None
    prompt_template: Any = None
    duration_s: float | None = None
    duration_ms: int | None = None


class ChatResponse(CustomBaseModel):
    question: str
    rewritten: str = ""
    symbol: str | None = None
    intent: str = ""
    agents_to_call: list[str] = Field(default_factory=list)
    route: str = ""
    reason: str = ""
    answer: str
    steps: list[ChatStep] = Field(default_factory=list)
    hitl_used: bool = False
    pending_approvals_created: int = 0
    error: str | None = None
    price: dict[str, Any] | None = None
    news_count: int = 0
    news: list[dict[str, Any]] = Field(default_factory=list)
    news_error: str | None = None
    severity: dict[str, Any] | None = None
    chart_path: str | None = None
    source_file: str | None = None
    session_id: str | None = None
    message_id: str | None = None
