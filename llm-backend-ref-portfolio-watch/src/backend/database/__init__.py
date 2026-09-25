"""Database package for Portfolio Watch V4.

Exports database connection helpers and CRUD repositories for:
- Sessions
- Messages
- Market History (10D)
- Human-in-the-loop (HITL) evaluations
- Watchlist
"""

from __future__ import annotations

from backend.database.connection import get_connection, get_db_path, init_db
from backend.database.repositories import (
    HITLEvaluationRecord,
    HITLEvaluationRepository,
    MarketHistoryRecord,
    MarketHistoryRepository,
    MessageRecord,
    MessageRepository,
    SessionRecord,
    SessionRepository,
    WatchlistRecord,
    WatchlistRepository,
)

__all__ = [
    "get_connection",
    "get_db_path",
    "init_db",
    "SessionRecord",
    "SessionRepository",
    "MessageRecord",
    "MessageRepository",
    "MarketHistoryRecord",
    "MarketHistoryRepository",
    "HITLEvaluationRecord",
    "HITLEvaluationRepository",
    "WatchlistRecord",
    "WatchlistRepository",
]
