"""Tests for Web Backend Application Layer (Use Cases)."""

import pytest
import sqlite3
from unittest.mock import MagicMock

from common.base.base_service import AsyncBaseService, BaseService
from web_backend.application.chat_gateway_service import (
    ChatGatewayInput,
    ChatGatewayOutput,
    ChatGatewayService,
)
from web_backend.application.hitl_service import (
    HitlFeedbackInput,
    HitlFeedbackOutput,
    HitlService,
    score_for_signal,
)
from web_backend.application.market_service import (
    MarketInput,
    MarketOutput,
    MarketService,
)
from web_backend.application.portfolio_service import (
    PortfolioInput,
    PortfolioItemSummary,
    PortfolioOutput,
    PortfolioService,
    PortfolioSummary,
)
from web_backend.application.review_approval_service import (
    ReviewApprovalInput,
    ReviewApprovalOutput,
    ReviewApprovalService,
)


def test_services_inherit_base_service():
    """Verify that all application services adhere to Clean Architecture BaseService contract."""
    assert issubclass(PortfolioService, BaseService)
    assert issubclass(HitlService, BaseService)
    assert issubclass(MarketService, BaseService)
    assert issubclass(ReviewApprovalService, BaseService)
    assert issubclass(ChatGatewayService, AsyncBaseService)


def test_portfolio_service_pnl_calculations():
    # Mock holdings repo
    mock_holding = MagicMock()
    mock_holding.id = "1"
    mock_holding.user_id = "test_user"
    mock_holding.symbol = "FPT"
    mock_holding.quantity = 100
    mock_holding.avg_buy_price = 60.0  # nghìn VND -> 60,000 VND
    mock_holding.purchase_date = "2026-01-01"

    mock_holdings_repo = MagicMock()
    mock_holdings_repo.list_by_user.return_value = [mock_holding]

    # Mock user settings
    mock_settings_repo = MagicMock()

    # Mock price source returning 66.0 nghìn VND (10% gain)
    mock_price_source = MagicMock()
    mock_quote = MagicMock()
    mock_quote.latest_close = 66.0
    mock_quote.error = None
    mock_price_source.fetch_latest_close.return_value = mock_quote

    service = PortfolioService(
        holdings_repo=mock_holdings_repo,
        user_settings_repo=mock_settings_repo,
        price_source=mock_price_source,
    )

    # Test process method
    inp = PortfolioInput(user_id="test_user", action="summary")
    res = service.process(inp)

    assert isinstance(res, PortfolioOutput)
    assert res.user_id == "test_user"
    assert res.count == 1
    assert res.total_cost == 6_000_000.0  # 100 * 60,000
    assert res.total_nav == 6_600_000.0   # 100 * 66,000
    assert res.total_unrealized_pnl == 600_000.0
    assert round(res.total_pnl_pct, 1) == 10.0


def test_hitl_service_signal_scoring():
    score_up, src_up = score_for_signal("thumbs_up")
    assert score_up == 1.0
    assert src_up == "explicit"

    score_down, src_down = score_for_signal("thumbs_down")
    assert score_down == 0.0
    assert src_down == "explicit"

    score_unknown, _ = score_for_signal("unknown_signal")
    assert score_unknown is None


def test_hitl_service_process():
    service = HitlService()
    inp = HitlFeedbackInput(
        question="Giá FPT?",
        answer="FPT đang ở mức 66.0",
        rating=1,
        is_positive=True,
        reason="thumbs_up",
        feedback_text="Rất chuẩn xác",
    )
    out = service.process(inp)

    assert isinstance(out, HitlFeedbackOutput)
    assert out.is_positive is True
    assert out.signal_score == 1.0
    assert out.feedback_text == "Rất chuẩn xác"
    assert out.id is not None


def test_market_service_process():
    service = MarketService()

    inp = MarketInput(action="sessions")
    out = service.process(inp)

    assert isinstance(out, MarketOutput)
    assert len(out.sessions) > 0
    session_types = [s["session_type"] for s in out.sessions]
    assert "ATO" in session_types
    assert "ATC" in session_types


def test_review_approval_service_process():
    service = ReviewApprovalService()

    # Test approve action
    inp_appr = ReviewApprovalInput(approval_id="APP-001", action="approve")
    out_appr = service.process(inp_appr)
    assert isinstance(out_appr, ReviewApprovalOutput)
    assert out_appr.approval_id == "APP-001"
    assert out_appr.status == "approved"

    # Test reject action
    inp_rej = ReviewApprovalInput(approval_id="APP-002", action="reject", reason="Rủi ro cao")
    out_rej = service.process(inp_rej)
    assert isinstance(out_rej, ReviewApprovalOutput)
    assert out_rej.approval_id == "APP-002"
    assert out_rej.status == "rejected"


@pytest.mark.asyncio
async def test_chat_gateway_service_process():
    service = ChatGatewayService(answer_fn=lambda q, **kwargs: f"Answer for {q}")
    inp = ChatGatewayInput(question="Hôm nay mua gì?", user_id="test_user")
    out = await service.process(inp)

    assert isinstance(out, ChatGatewayOutput)
    assert out.question == "Hôm nay mua gì?"
    assert "Answer for Hôm nay mua gì?" in out.answer
    assert out.session_id is not None
    assert out.message_id is not None
