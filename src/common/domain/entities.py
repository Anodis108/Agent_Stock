"""Domain entities — pydantic thuần kế thừa CustomBaseModel, không phụ thuộc infra."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import Field

from common.base.base_model import CustomBaseModel


class EventRoute(str, Enum):
    """Kết quả Event Classifier (nhánh giám sát)."""

    NORMAL = "bình thường"
    ABNORMAL = "bất thường"


class SeverityLevel(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AlertStatus(str, Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    SENT = "sent"
    REJECTED = "rejected"


class User(CustomBaseModel):
    """Thực thể người dùng trong hệ thống đa tài khoản."""

    user_id: str = "default"
    username: str = "Default User"
    risk_profile: str = "moderate"
    alert_threshold_pct: float = 3.0


class Holding(CustomBaseModel):
    """Thực thể cổ phiếu nắm giữ trong danh mục đầu tư."""

    user_id: str = "default"
    ticker: str = Field(min_length=1)
    shares: int = Field(ge=0)
    buy_price: float = Field(ge=0.0)
    buy_date: str = ""
    current_price: float | None = None
    market_value: float | None = None
    unrealized_pnl: float | None = None
    unrealized_pnl_pct: float | None = None


class WatchlistItem(CustomBaseModel):
    """Thực thể mã cổ phiếu trong danh sách theo dõi."""

    symbol: str = Field(min_length=1)
    threshold_pct: float = Field(ge=0, description="Ngưỡng % biến động để cảnh báo")
    user_id: str = "default"
    created_at: str | None = None


class Message(CustomBaseModel):
    """Thực thể tin nhắn trong phiên hội thoại."""

    session_id: str
    role: str  # "user" | "assistant" | "system"
    content: str
    created_at: str | None = None
    feedback: str | None = None  # "like" | "dislike" | None


class StockQuote(CustomBaseModel):
    """Thực thể báo giá thị trường cổ phiếu."""

    symbol: str
    latest_close: float | None = None
    prev_close: float | None = None
    change_pct: float | None = None
    volume: float | None = None
    error: str | None = None


class RoutingDecision(CustomBaseModel):
    """Quyết định định tuyến — giám sát (Event Classifier) hoặc hỏi-đáp (Supervisor)."""

    route: EventRoute | str
    reason: str = ""
    agents_to_call: list[str] = Field(
        default_factory=list,
        description="Nhánh hỏi-đáp: agent cần gọi (price, news, eval, …)",
    )


class Severity(CustomBaseModel):
    level: SeverityLevel
    confidence: float = Field(ge=0, le=1)
    reasoning: str
    evidence: list[str] = Field(default_factory=list)
    proposed_threshold_pct: float | None = None
    proposed_related_symbols: list[str] = Field(default_factory=list)


class FinalAlert(CustomBaseModel):
    """Cảnh báo nhánh giám sát — status phục vụ Confidence Gate / HITL Gate 1."""

    id: str | None = None
    symbol: str = Field(min_length=1)
    title: str
    body: str
    severity: Severity
    status: AlertStatus = AlertStatus.DRAFT
    reject_reason: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
