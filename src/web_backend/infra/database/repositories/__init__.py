"""Database repositories package for Web Backend.

Exports entity records and repository classes:
- SessionRepository / SessionRepo
- MessageRepository / MessageRepo
- PortfolioHoldingRepository / PortfolioRepo
- UserSettingsRepository / UserSettingsRepo
- WatchlistRepository / WatchlistRepo
- HITLEvaluationRepository / HITLEvalRepo
- MarketHistoryRepository / MarketHistoryRepo
"""

from __future__ import annotations

from web_backend.infra.database.repositories.hitl_repo import (
    HITLEvaluationRecord,
    HITLEvaluationRepository,
    HITLEvalRepo,
)
from web_backend.infra.database.repositories.market_history_repo import (
    MarketHistoryRecord,
    MarketHistoryRepository,
    MarketHistoryRepo,
)
from web_backend.infra.database.repositories.message_repo import (
    MessageRecord,
    MessageRepository,
    MessageRepo,
)
from web_backend.infra.database.repositories.portfolio_repo import (
    PortfolioHoldingRecord,
    PortfolioHoldingRepository,
    PortfolioRepo,
    UserSettingsRecord,
    UserSettingsRepository,
    UserSettingsRepo,
)
from web_backend.infra.database.repositories.session_repo import (
    SessionRecord,
    SessionRepository,
    SessionRepo,
)
from web_backend.infra.database.repositories.watchlist_repo import (
    WatchlistRecord,
    WatchlistRepository,
    WatchlistRepo,
)

__all__ = [
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
