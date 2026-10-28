"""Pydantic schemas for AI Backend SSE Streaming and LangGraph Swarm Events."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import Field

from common.base.base_model import CustomBaseModel


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class WatchlistSnapshot(CustomBaseModel):
    """Ảnh chụp nhanh danh mục theo dõi được gửi từ Web Backend."""
    symbol: str
    threshold_pct: float = 3.0
    user_id: str = Field(min_length=1)


class HoldingSnapshot(CustomBaseModel):
    """Ảnh chụp nhanh vị thế nắm giữ được gửi từ Web Backend."""
    symbol: str
    quantity: float
    avg_buy_price: float
    user_id: str = Field(min_length=1)


class ChatStreamRequest(CustomBaseModel):
    """Yêu cầu stream hội thoại gửi tới AI Backend (POST /v1/chat/stream)."""
    question: str = Field(description="Nội dung câu hỏi của người dùng")
    user_id: str = Field(min_length=1, description="Mã định danh người dùng")
    session_id: str | None = Field(default=None, description="Mã phiên hội thoại")
    request_id: str = Field(min_length=1, description="Mã tương quan yêu cầu (web backend sinh ở biên)")


class TokenEvent(CustomBaseModel):
    """Sự kiện phát từng token sinh ra từ AnswerComposer hoặc Agent LLM."""
    event: str = "token"
    token: str = Field(description="Đoạn văn bản token vừa sinh")
    node: str = Field(default="answer", description="Node phát token")
    index: int = Field(default=0, description="Thứ tự token trong luồng stream")


class CompleteEvent(CustomBaseModel):
    """Sự kiện báo hiệu toàn bộ pipeline Swarm đã xử lý xong và trả kết quả tổng hợp."""
    event: str = "complete"
    answer: str = Field(description="Nội dung câu trả lời hoàn chỉnh")
    route: str = Field(default="market", description="Luồng định tuyến (market, technical, concept, ...)")
    steps: list[dict[str, Any]] = Field(default_factory=list, description="Tiến trình các bước thực thi")
    request_id: str | None = Field(default=None, description="Mã yêu cầu")
    source_file: str | None = Field(default=None, description="Nguồn trích dẫn khái niệm nếu có")
    symbol: str | None = Field(default=None, description="Mã chứng khoán trọng tâm nếu có")
    price: dict[str, Any] | None = Field(default=None, description="Thông tin giá mới nhất")
    news_count: int = Field(default=0, description="Số lượng tin tức liên quan")


class ErrorEvent(CustomBaseModel):
    """Sự kiện báo lỗi trong quá trình xử lý luồng stream."""
    event: str = "error"
    error: str = Field(description="Mô tả thông báo lỗi")
    request_id: str | None = Field(default=None, description="Mã yêu cầu")


class ChatResponse(CustomBaseModel):
    """Phản hồi JSON POST /v1/chat (cùng shape ChatOutput)."""
    question: str
    answer: str
    steps: list[dict[str, Any]] = Field(default_factory=list)
    drawed_paths: list[str] = Field(default_factory=list)
