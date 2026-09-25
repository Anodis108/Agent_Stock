"""Domain entities — pydantic thuần, không phụ thuộc infra."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class EventRoute(str, Enum):
    """Kết quả Event Classifier (nhánh giám sát)."""

    NORMAL = "bình thường"
    ABNORMAL = "bất thường"


class SeverityLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AlertStatus(str, Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    SENT = "sent"
    REJECTED = "rejected"


class WatchlistItem(BaseModel):
    symbol: str = Field(min_length=1)
    threshold_pct: float = Field(ge=0, description="Ngưỡng % biến động để cảnh báo")
    user_id: str = "default"


class RoutingDecision(BaseModel):
    """Quyết định định tuyến — giám sát (Event Classifier) hoặc hỏi-đáp (Supervisor)."""

    route: EventRoute | str
    reason: str = ""
    agents_to_call: list[str] = Field(
        default_factory=list,
        description="Nhánh hỏi-đáp: agent cần gọi (price, news, eval, …)",
    )


class Severity(BaseModel):
    level: SeverityLevel
    confidence: float = Field(ge=0, le=1)
    reasoning: str
    evidence: list[str] = Field(default_factory=list)
    # Đề xuất cấu hình → luôn qua HITL Gate 2 khi có
    proposed_threshold_pct: float | None = None
    proposed_related_symbols: list[str] = Field(default_factory=list)


class FinalAlert(BaseModel):
    """Cảnh báo nhánh giám sát — status phục vụ Confidence Gate / HITL Gate 1."""

    id: str | None = None
    symbol: str = Field(min_length=1)
    title: str
    body: str
    severity: Severity
    status: AlertStatus = AlertStatus.DRAFT
    reject_reason: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
