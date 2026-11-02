"""Database package for Web Backend.

Exports connection helpers and repositories.
"""

from __future__ import annotations

from web_backend.infra.database.connection import (
    DEFAULT_SCHEMA,
    get_connection,
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
    HITLEvalRepo,
    HITLEvaluationRecord,
    HITLEvaluationRepository,
    MarketHistoryRecord,
    MarketHistoryRepo,
    MarketHistoryRepository,
    MessageRecord,
    MessageRepo,
    MessageRepository,
    PortfolioHoldingRecord,
    PortfolioHoldingRepository,
    PortfolioRepo,
    SessionRecord,
    SessionRepo,
    SessionRepository,
    UserSettingsRecord,
    UserSettingsRepo,
    UserSettingsRepository,
    WatchlistRecord,
    WatchlistRepo,
    WatchlistRepository,
)

__all__ = [
    "DEFAULT_SCHEMA",
    "get_connection",
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
