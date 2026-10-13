"""Watchlist và holdings do web đọc rồi gửi sang AI. AI không SELECT bảng session."""

from __future__ import annotations

import re

from backend.domain.entities import WatchlistItem

_ACCOUNT_NEEDLES = (
    "danh mục",
    "portfolio",
    "lãi lỗ",
    "lãi/lỗ",
    "lãi hay lỗ",
    "nav",
    "tài khoản",
    "nắm giữ",
    "vị thế",
    "holdings",
    "watchlist",
    "theo dõi",
    "danh sách theo dõi",
    "mã theo dõi",
    "ngưỡng cảnh báo",
    "giá",
    "biểu đồ",
    "nến",
    "chart",
)
_TICKER = re.compile(r"\b[A-Z]{3}\b")
_NOT_TICKERS = frozenset({"RSI", "SMA", "EMA", "ATO", "ATC", "NAV"})
_CONCEPT_NEEDLES = (
    "là gì",
    "la gi",
    "định nghĩa",
    "dinh nghia",
    "khái niệm",
    "khai niem",
    "giá trần",
    "gia tran",
    "giá sàn",
    "gia san",
    "biên độ",
    "bien do",
    "ato",
    "atc",
    "lệnh lo",
    "lenh lo",
    "rsi",
    "sma",
    "nav",
    "lãi lỗ chưa chốt",
    "lai lo chua chot",
    "chưa chốt",
    "chua chot",
    "miễn trừ",
    "mien tru",
)
_OWN_ACCOUNT = (
    "của tôi",
    "cua toi",
    "của mình",
    "cua minh",
    "của user",
    "cua user",
)


def _live_tickers(text: str) -> list[str]:
    return [match for match in _TICKER.findall(text or "") if match not in _NOT_TICKERS]


def is_concept_question(question: str) -> bool:
    """Định nghĩa trong năm file khái niệm. Mã cụ thể hoặc danh mục của user thì không phải."""
    text = question or ""
    if _live_tickers(text):
        return False
    folded = text.casefold()
    if any(needle in folded for needle in _OWN_ACCOUNT):
        return False
    return any(needle in folded for needle in _CONCEPT_NEEDLES)


def question_needs_account_lists(question: str) -> bool:
    """Câu số liệu hoặc danh mục thì web gửi hai danh sách. Câu khái niệm và câu chào thì không."""
    if is_concept_question(question):
        return False
    text = question or ""
    folded = text.casefold()
    if any(needle in folded for needle in _ACCOUNT_NEEDLES):
        return True
    return bool(_live_tickers(text))


def load_account_snapshot(user_id: str) -> dict[str, list[dict]]:
    """Đọc watchlist trang web và holdings danh mục của đúng user."""
    from backend.deps import get_app_deps
    from backend.routes.watchlist import store as watchlist_store

    uid = (user_id or "default").strip() or "default"
    watchlist = [
        {
            "symbol": item.symbol,
            "threshold_pct": float(item.threshold_pct),
            "user_id": getattr(item, "user_id", uid) or uid,
        }
        for item in watchlist_store.list_watchlist(uid) or []
    ]
    holdings: list[dict] = []
    repo = getattr(get_app_deps(), "holdings_repo", None)
    if repo is not None:
        for row in repo.list_by_user(uid) or []:
            holdings.append(
                {
                    "symbol": row.symbol,
                    "quantity": float(row.quantity),
                    "avg_buy_price": float(row.avg_buy_price),
                    "user_id": row.user_id,
                }
            )
    return {"watchlist": watchlist, "holdings": holdings}


class SnapshotWatchlistStore:
    """Watchlist lấy từ body HTTP. Không mở bảng watchlist."""

    def __init__(self, items: list[WatchlistItem]):
        self._items = list(items)

    def list_items(self, user_id: str = "default") -> list[WatchlistItem]:
        uid = (user_id or "default").strip() or "default"
        return [item for item in self._items if item.user_id == uid]

    def get(self, user_id: str, symbol: str) -> WatchlistItem | None:
        wanted = (symbol or "").strip().upper()
        for item in self.list_items(user_id):
            if item.symbol.strip().upper() == wanted:
                return item
        return None

    def upsert(self, item: WatchlistItem) -> WatchlistItem:
        self.delete(item.user_id, item.symbol)
        self._items.append(item)
        return item

    def delete(self, user_id: str, symbol: str) -> bool:
        wanted = (symbol or "").strip().upper()
        kept: list[WatchlistItem] = []
        removed = False
        for item in self._items:
            if item.user_id == user_id and item.symbol.strip().upper() == wanted:
                removed = True
                continue
            kept.append(item)
        self._items = kept
        return removed
