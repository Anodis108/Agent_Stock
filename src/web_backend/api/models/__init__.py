"""Pydantic Models Package for Web Backend API."""

from web_backend.api.models.approvals import (
    ApproveRequest,
    ApprovalsListResponse,
    RejectRequest,
    ReviewResponse,
)
from web_backend.api.models.chat import (
    ChatRequest,
    ChatResponse,
    ChatStep,
)
from web_backend.api.models.hitl import (
    FeedbackCreateRequest,
    FeedbackListResponse,
    FeedbackOut,
)
from web_backend.api.models.market import (
    MarketMatrixItemOut,
    MarketMatrixResponse,
    MarketSessionOut,
)
from web_backend.api.models.portfolio import (
    CreateHoldingRequest,
    HoldingOut,
    PortfolioItemOut,
    PortfolioSummaryOut,
    UpdateUserSettingsRequest,
    UserSettingsOut,
)
from web_backend.api.models.scan import (
    ScanRequest,
    ScanResponse,
)
from web_backend.api.models.sessions import (
    CreateSessionRequest,
    MessageOut,
    SessionDetailResponse,
    SessionListResponse,
    SessionOut,
)
from web_backend.api.models.watchlist import (
    CreateWatchlistRequest,
    UpdateWatchlistRequest,
    WatchlistItemOut,
    WatchlistListResponse,
)

__all__ = [
    "ChatRequest",
    "ChatStep",
    "ChatResponse",
    "CreateHoldingRequest",
    "HoldingOut",
    "PortfolioItemOut",
    "PortfolioSummaryOut",
    "UserSettingsOut",
    "UpdateUserSettingsRequest",
    "FeedbackCreateRequest",
    "FeedbackOut",
    "FeedbackListResponse",
    "SessionOut",
    "SessionListResponse",
    "CreateSessionRequest",
    "MessageOut",
    "SessionDetailResponse",
    "WatchlistItemOut",
    "WatchlistListResponse",
    "CreateWatchlistRequest",
    "UpdateWatchlistRequest",
    "MarketSessionOut",
    "MarketMatrixItemOut",
    "MarketMatrixResponse",
    "ApproveRequest",
    "RejectRequest",
    "ReviewResponse",
    "ApprovalsListResponse",
    "ScanRequest",
    "ScanResponse",
]
