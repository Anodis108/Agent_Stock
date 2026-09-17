from __future__ import annotations

from typing import Any

from src.portfolio_watch.domain.ports import NewsItem, PriceBar, PriceQuote
from src.portfolio_watch.domain.entities import WatchlistItem


class FakePriceSource:
    def __init__(self, quote: PriceQuote):
        self._quote = quote

    def fetch_latest_close(self, symbol: str) -> PriceQuote:
        return PriceQuote(
            symbol=symbol,
            latest_close=self._quote.latest_close,
            prev_close=self._quote.prev_close,
            error=self._quote.error,
        )


class FakeNewsSource:
    """Trả tin theo thứ tự lần gọi (phục vụ test vòng lặp ReAct)."""

    def __init__(self, batches: list[list[NewsItem]]):
        self._batches = list(batches)
        self.calls: list[tuple[str, str | None, int | None]] = []

    def fetch_news(
        self,
        symbol: str,
        query: str | None = None,
        *,
        days: int | None = None,
    ) -> list[NewsItem]:
        self.calls.append((symbol, query, days))
        if not self._batches:
            return []
        return self._batches.pop(0)


class FakePriceHistoryStore:
    def __init__(self, bars: list[PriceBar]):
        self._bars = bars
        self.calls: list[tuple[str, int]] = []

    def read_history(self, symbol: str, days: int = 30) -> list[PriceBar]:
        self.calls.append((symbol, days))
        return list(self._bars)


class FakeMemoryStore:
    def __init__(self, preferences: dict[str, Any] | None = None):
        self._preferences = preferences or {}
        self.rejections: list[dict[str, Any]] = []
        self.alert_events: list[tuple[str, dict[str, Any]]] = []
        self.conversations: list[tuple[str, str, str]] = []

    def read_preferences(self, user_id: str = "default") -> dict[str, Any]:
        return dict(self._preferences)

    def write_preferences(self, user_id: str, preferences: dict[str, Any]) -> None:
        self._preferences = dict(preferences)

    def append_conversation(self, user_id: str, role: str, content: str) -> None:
        self.conversations.append((user_id, role, content))

    def list_conversation(self, user_id: str, limit: int = 20) -> list[dict[str, Any]]:
        items = [
            {"role": role, "content": content}
            for uid, role, content in self.conversations
            if uid == user_id
        ]
        return items[-max(limit, 1) :]

    def append_alert_event(self, user_id: str, event: dict[str, Any]) -> None:
        self.alert_events.append((user_id, dict(event)))

    def list_alert_events(self, user_id: str, limit: int = 20) -> list[dict[str, Any]]:
        items = [dict(e) for uid, e in self.alert_events if uid == user_id]
        return items[-max(limit, 1) :]

    def record_rejection(
        self,
        user_id: str,
        *,
        gate: str,
        reason: str,
        context: dict[str, Any] | None = None,
    ) -> None:
        self.rejections.append(
            {"user_id": user_id, "gate": gate, "reason": reason, "context": context}
        )


class FakeNotifier:
    def __init__(self):
        self.sent: list[Any] = []

    def send(self, alert: Any) -> None:
        from src.portfolio_watch.domain.entities import AlertStatus

        if getattr(alert, "status", None) == AlertStatus.REJECTED:
            return
        alert.status = AlertStatus.SENT
        self.sent.append(alert)


class FakeWatchlistStore:
    def __init__(self, items: list[WatchlistItem] | None = None):
        self._items: dict[tuple[str, str], WatchlistItem] = {}
        self.upserts: list[WatchlistItem] = []
        for item in items or []:
            self._items[(item.user_id, item.symbol.upper())] = item

    def list_items(self, user_id: str = "default") -> list[WatchlistItem]:
        return [i for (uid, _), i in self._items.items() if uid == user_id]

    def get(self, user_id: str, symbol: str) -> WatchlistItem | None:
        return self._items.get((user_id, symbol.strip().upper()))

    def upsert(self, item: WatchlistItem) -> WatchlistItem:
        self.upserts.append(item)
        self._items[(item.user_id, item.symbol.upper())] = item
        return item

    def delete(self, user_id: str, symbol: str) -> bool:
        return self._items.pop((user_id, symbol.strip().upper()), None) is not None
