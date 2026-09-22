"""Ports (interfaces) — domain chỉ phụ thuộc các contract này, không import infra."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from src.portfolio_watch.domain.entities import FinalAlert, WatchlistItem


@dataclass(slots=True)
class PriceQuote:
    """Giá mới nhất (+ phiên trước) cho PriceAgent."""

    symbol: str
    latest_close: float | None
    prev_close: float | None = None
    error: str | None = None


@dataclass(slots=True)
class NewsItem:
    title: str
    url: str = ""
    published_at: str | None = None
    snippet: str = ""
    symbol: str | None = None


@dataclass(slots=True)
class PriceBar:
    date: str
    close: float
    open_price: float | None = None
    high: float | None = None
    low: float | None = None
    volume: float | None = None


class PriceSource(Protocol):
    def fetch_latest_close(self, symbol: str) -> PriceQuote:
        """Lấy giá đóng cửa mới nhất (và phiên trước nếu có).

        Lỗi / không có dữ liệu: trả `PriceQuote` với `error` set,
        `latest_close=None` — không raise mơ hồ / không trả None.
        """
        ...


class NewsSource(Protocol):
    def fetch_news(
        self,
        symbol: str,
        query: str | None = None,
        *,
        days: int | None = None,
    ) -> list[NewsItem]:
        """Lấy tin theo mã / từ khóa (+ khung thời gian `days` nếu có)."""
        ...


class WatchlistStore(Protocol):
    def list_items(self, user_id: str = "default") -> list[WatchlistItem]:
        ...

    def get(self, user_id: str, symbol: str) -> WatchlistItem | None:
        ...

    def upsert(self, item: WatchlistItem) -> WatchlistItem:
        ...

    def delete(self, user_id: str, symbol: str) -> bool:
        ...


class PriceHistoryStore(Protocol):
    def read_history(self, symbol: str, days: int = 30) -> list[PriceBar]:
        """Lịch sử giá — EvalAgent gọi khi cần thêm căn cứ."""
        ...


class MemoryStore(Protocol):
    def read_preferences(self, user_id: str = "default") -> dict[str, Any]:
        ...

    def write_preferences(self, user_id: str, preferences: dict[str, Any]) -> None:
        ...

    def append_conversation(
        self,
        user_id: str,
        role: str,
        content: str,
        *,
        created_at: str | None = None,
    ) -> None:
        ...

    def list_conversation(
        self,
        user_id: str,
        limit: int | None = None,
        *,
        ttl_minutes: int | float | None = None,
    ) -> list[dict[str, Any]]:
        ...

    def append_alert_event(
        self, user_id: str, event: dict[str, Any]
    ) -> None:
        """Lưu lịch sử cảnh báo (đã gửi / chờ duyệt / reject…)."""
        ...

    def list_alert_events(
        self, user_id: str, limit: int = 20
    ) -> list[dict[str, Any]]:
        ...

    def record_rejection(
        self,
        user_id: str,
        *,
        gate: str,
        reason: str,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Ghi lý do reject HITL Gate 1 / Gate 2."""
        ...


class Notifier(Protocol):
    def send(self, alert: FinalAlert) -> None:
        """Gửi cảnh báo (MVP: console + ghi DB)."""
        ...
