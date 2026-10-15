"""Database package for Web Backend.

Exports connection helpers and repositories.
"""

from __future__ import annotations

from web_backend.infra.database.connection import (
    get_connection,
    get_db_path,
    init_db,
)
from web_backend.infra.database.pg import (
    PgConn,
    PgCursor,
    PgRow,
    connect_postgres,
    qmark,
    schema_name,
)
from web_backend.infra.database.repositories import (
    HITLEvaluationRecord,
    HITLEvaluationRepository,
    HITLEvalRepo,
    MarketHistoryRecord,
    MarketHistoryRepository,
    MarketHistoryRepo,
    MessageRecord,
    MessageRepository,
    MessageRepo,
    PortfolioHoldingRecord,
    PortfolioHoldingRepository,
    PortfolioRepo,
    SessionRecord,
    SessionRepository,
    SessionRepo,
    UserSettingsRecord,
    UserSettingsRepository,
    UserSettingsRepo,
    WatchlistRecord,
    WatchlistRepository,
    WatchlistRepo,
)

__all__ = [
    "get_connection",
    "get_db_path",
    "init_db",
    "connect_postgres",
    "PgConn",
    "PgCursor",
    "PgRow",
    "qmark",
    "schema_name",
    "SessionRecord",
    "SessionRepository",
    "SessionRepo",
    "MessageRecord",
    "MessageRepository",
    "MessageRepo",
    "PortfolioHoldingRecord",
    "PortfolioHoldingRepository",
    "PortfolioRepo",
    "UserSettingsRecord",
    "UserSettingsRepository",
    "UserSettingsRepo",
    "WatchlistRecord",
    "WatchlistRepository",
    "WatchlistRepo",
    "HITLEvaluationRecord",
    "HITLEvaluationRepository",
    "HITLEvalRepo",
    "MarketHistoryRecord",
    "MarketHistoryRepository",
    "MarketHistoryRepo",
]
