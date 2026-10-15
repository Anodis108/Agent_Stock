"""Unit tests for Web Backend Domain Layer (SessionValidator & PortfolioCalculator)."""

from __future__ import annotations

import pytest

from web_backend.domain.portfolio_calculator import (
    HoldingCalculationResult,
    PortfolioAlert,
    PortfolioCalculationResult,
    PortfolioCalculator,
)
from web_backend.domain.session_validator import (
    SessionValidationResult,
    SessionValidator,
)


class TestSessionValidator:
    """Kiểm thử xác thực tính hợp lệ của session, user và input dữ liệu."""

    def test_session_id_valid(self) -> None:
        valid_ids = [
            "session-123",
            "session_abc_XYZ",
            "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            "test123",
        ]
        for sid in valid_ids:
            res = SessionValidator.validate_session_id(sid)
            assert res.is_valid is True
            assert res.clean_value == sid

    def test_session_id_empty_or_none(self) -> None:
        for val in [None, "", "   "]:
            res = SessionValidator.validate_session_id(val)
            assert res.is_valid is True
            assert res.clean_value is None

    def test_session_id_invalid_traversal_and_null(self) -> None:
        invalid_ids = [
            "../../etc/passwd",
            "session/subfolder",
            "session\\win",
            "session\0null",
            "session;DROP TABLE",
            "s@#$%",
            "a" * 130,  # > 128 chars
        ]
        for sid in invalid_ids:
            res = SessionValidator.validate_session_id(sid)
            assert res.is_valid is False
            assert "không hợp lệ" in res.error_message or "1-128" in res.error_message

    def test_user_id_valid(self) -> None:
        valid_users = ["default", "user_a", "user_b", "investor-01", "user@example.com"]
        for uid in valid_users:
            res = SessionValidator.validate_user_id(uid)
            assert res.is_valid is True
            assert res.clean_value == uid

    def test_user_id_empty_or_none_defaults_to_default(self) -> None:
        for val in [None, "", "   "]:
            res = SessionValidator.validate_user_id(val)
            assert res.is_valid is True
            assert res.clean_value == "default"

    def test_user_id_invalid(self) -> None:
        invalid_users = [
            "user/admin",
            "user\\admin",
            "user\0name",
            "u" * 70,  # > 64 chars
        ]
        for uid in invalid_users:
            res = SessionValidator.validate_user_id(uid)
            assert res.is_valid is False

    def test_chat_input_validation(self) -> None:
        # Valid questions
        res1 = SessionValidator.validate_chat_input("Giá FPT hôm nay bao nhiêu?")
        assert res1.is_valid is True
        assert res1.clean_value == "Giá FPT hôm nay bao nhiêu?"

        # Empty question
        res2 = SessionValidator.validate_chat_input("   ")
        assert res2.is_valid is False
        assert "không được để trống" in res2.error_message

        # Null byte
        res3 = SessionValidator.validate_chat_input("Hỏi \0 mã FPT")
        assert res3.is_valid is False

        # Exceeds max length
        res4 = SessionValidator.validate_chat_input("A" * 105, max_length=100)
        assert res4.is_valid is False
        assert "vượt quá độ dài" in res4.error_message

    def test_title_validation(self) -> None:
        # Empty title defaults
        res1 = SessionValidator.validate_title("")
        assert res1.is_valid is True
        assert res1.clean_value == "Cuộc trò chuyện mới"

        # Valid title
        res2 = SessionValidator.validate_title("Phân tích kỹ thuật FPT")
        assert res2.is_valid is True
        assert res2.clean_value == "Phân tích kỹ thuật FPT"

        # Long title gets truncated
        long_title = "B" * 250
        res3 = SessionValidator.validate_title(long_title, max_length=200)
        assert res3.is_valid is True
        assert len(res3.clean_value) == 200

    def test_holding_input_validation(self) -> None:
        # Valid holding
        res1 = SessionValidator.validate_holding_input("fpt", 100, 52.5)
        assert res1.is_valid is True
        assert res1.clean_value == {"symbol": "FPT", "quantity": 100, "buy_price": 52.5}

        # Invalid symbol
        res2 = SessionValidator.validate_holding_input("TOOLONGSYMBOL", 100, 50.0)
        assert res2.is_valid is False

        # Invalid quantity
        res3 = SessionValidator.validate_holding_input("HPG", 0, 25.0)
        assert res3.is_valid is False

        # Invalid buy price
        res4 = SessionValidator.validate_holding_input("VNM", 50, -10.0)
        assert res4.is_valid is False


class TestPortfolioCalculator:
    """Kiểm thử tính toán tài chính thuần túy cho danh mục đầu tư."""

    def test_normalize_price_vnd(self) -> None:
        assert PortfolioCalculator.normalize_price_vnd(None) is None
        # Giá niêm yết theo nghìn đồng (<= 1000)
        assert PortfolioCalculator.normalize_price_vnd(52.5) == 52500.0
        assert PortfolioCalculator.normalize_price_vnd(100.0) == 100000.0
        assert PortfolioCalculator.normalize_price_vnd(1000.0) == 1000000.0
        # Giá niêm yết theo VND đầy đủ (> 1000)
        assert PortfolioCalculator.normalize_price_vnd(52500.0) == 52500.0
        assert PortfolioCalculator.normalize_price_vnd(1050.0) == 1050.0

    def test_calculate_item_pnl_profit(self) -> None:
        # Mua 1000 cổ FPT giá 100k, giá hiện tại 120k -> lãi 20 triệu (20%)
        res = PortfolioCalculator.calculate_item_pnl(
            quantity=1000,
            avg_buy_price=100.0,
            current_price=120.0,
            symbol="FPT",
            item_id="item-1",
        )
        assert res.symbol == "FPT"
        assert res.cost_basis == 100_000_000.0
        assert res.market_value == 120_000_000.0
        assert res.unrealized_pnl == 20_000_000.0
        assert res.pnl_pct == 20.0
        assert res.price_error is False

    def test_calculate_item_pnl_loss(self) -> None:
        # Mua 500 cổ HPG giá 30k, giá hiện tại 27k -> lỗ 1.5 triệu (-10%)
        res = PortfolioCalculator.calculate_item_pnl(
            quantity=500,
            avg_buy_price=30.0,
            current_price=27.0,
            symbol="HPG",
        )
        assert res.cost_basis == 15_000_000.0
        assert res.market_value == 13_500_000.0
        assert res.unrealized_pnl == -1_500_000.0
        assert res.pnl_pct == -10.0
        assert res.price_error is False

    def test_calculate_item_pnl_price_error_fallback(self) -> None:
        # Giá hiện tại bị None hoặc <= 0 -> fallback thị giá bằng giá vốn, pnl = 0
        res = PortfolioCalculator.calculate_item_pnl(
            quantity=200,
            avg_buy_price=50.0,
            current_price=None,
            symbol="MWG",
        )
        assert res.cost_basis == 10_000_000.0
        assert res.market_value == 10_000_000.0
        assert res.unrealized_pnl == 0.0
        assert res.pnl_pct == 0.0
        assert res.price_error is True

    def test_calculate_portfolio_summary_weights_and_concentration(self) -> None:
        holdings = [
            {"symbol": "FPT", "quantity": 1000, "avg_buy_price": 100.0, "current_price": 100.0},  # 100M
            {"symbol": "HPG", "quantity": 1000, "avg_buy_price": 25.0, "current_price": 25.0},    # 25M
            {"symbol": "VNM", "quantity": 1000, "avg_buy_price": 25.0, "current_price": 25.0},    # 25M
        ]
        # Tổng NAV = 150M. FPT = 100M / 150M = 66.67% (chạm cảnh báo tập trung >= 40%)
        summary = PortfolioCalculator.calculate_portfolio_summary(holdings, user_id="user_a")
        assert summary.user_id == "user_a"
        assert summary.total_cost == 150_000_000.0
        assert summary.total_nav == 150_000_000.0
        assert summary.total_unrealized_pnl == 0.0
        assert summary.total_pnl_pct == 0.0
        assert summary.holdings_count == 3

        weights = [it.weight_pct for it in summary.items]
        assert round(sum(weights), 1) == 100.0
        assert summary.concentration_warning is not None
        assert "FPT" in summary.concentration_warning

    def test_calculate_portfolio_summary_empty(self) -> None:
        summary = PortfolioCalculator.calculate_portfolio_summary([])
        assert summary.holdings_count == 0
        assert summary.total_nav == 0.0
        assert summary.total_cost == 0.0
        assert summary.total_unrealized_pnl == 0.0
        assert summary.concentration_warning is None

    def test_check_alert_triggers(self) -> None:
        items = [
            HoldingCalculationResult(
                symbol="FPT", quantity=100, avg_buy_price=100.0, current_price=115.0, pnl_pct=15.0
            ),
            HoldingCalculationResult(
                symbol="HPG", quantity=100, avg_buy_price=30.0, current_price=26.0, pnl_pct=-13.33
            ),
            HoldingCalculationResult(
                symbol="VNM", quantity=100, avg_buy_price=70.0, current_price=72.0, pnl_pct=2.86
            ),
            HoldingCalculationResult(
                symbol="VIC", quantity=100, avg_buy_price=40.0, current_price=None, pnl_pct=0.0, price_error=True
            ),
        ]

        alerts = PortfolioCalculator.check_alert_triggers(items, threshold_pct=10.0)
        assert len(alerts) == 2

        fpt_alert = next((a for a in alerts if a.symbol == "FPT"), None)
        assert fpt_alert is not None
        assert fpt_alert.alert_type == "TAKE_PROFIT"
        assert fpt_alert.pnl_pct == 15.0

        hpg_alert = next((a for a in alerts if a.symbol == "HPG"), None)
        assert hpg_alert is not None
        assert hpg_alert.alert_type == "STOP_LOSS"
        assert hpg_alert.pnl_pct == -13.33
