"""Kiểm thử Dịch vụ Thị trường (MarketService), Ma trận 10D và Đồng bộ Dữ liệu Giá.

Bao gồm:
1. MarketService: Khởi tạo danh sách 10 mã mặc định, đồng bộ nến ngày, tính toán ma trận 10D.
2. Market Watch API: Endpoint `/api/v1/market/matrix-10d`, tham số tùy chỉnh số ngày và danh sách mã.
3. Single Source of Truth (SSOT): Đồng bộ dữ liệu giá giữa Chat và Market Watch, cache nhất quán.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.domain.ports import PriceBar
from backend.infra.market_data.price_source import VnstockPriceSource
from backend.services.market_service import (
    DEFAULT_MARKET_SYMBOLS,
    MarketService,
    get_market_service,
)
from backend.main import app as product_app


# ==============================================================================
# 1. MarketService Core Logic Tests
# ==============================================================================

def test_default_market_symbols_count_and_items():
    """Kiểm tra danh sách 10 mã VN30 mặc định chuẩn xác."""
    expected = ["FPT", "VNM", "HPG", "VHM", "VIC", "TCB", "MBB", "SSI", "MWG", "VCB"]
    assert DEFAULT_MARKET_SYMBOLS == expected
    assert len(DEFAULT_MARKET_SYMBOLS) == 10


def test_get_matrix_10d_computation(real_deps):
    """Kiểm tra hàm get_matrix_10d trả về đúng cấu trúc ma trận kèm sparklines."""
    ms = MarketService(price_source=VnstockPriceSource())
    items = ms.get_matrix_10d(symbols=["FPT", "VNM"], days=5)

    assert isinstance(items, list)
    assert len(items) == 2
    for item in items:
        assert item["symbol"] in ("FPT", "VNM")
        assert "sparkline" in item
        assert "current_price" in item
        assert "change_pct" in item
        assert len(item["sparkline"]) == 5


def test_sync_symbol_history_fallback_on_empty(real_deps):
    """Kiểm tra cơ chế fallback sinh dữ liệu mẫu hợp lệ khi nguồn dữ liệu ngoài trả về rỗng."""
    ms = MarketService()
    # Đồng bộ một mã không có trên sàn thật -> kích hoạt fallback
    records = ms.get_symbol_history("XYZ", limit=5)
    assert len(records) > 0
    assert records[0].symbol == "XYZ"
    assert records[0].close > 0


# ==============================================================================
# 2. Market Watch API Endpoints Tests
# ==============================================================================

def test_get_matrix_10d_endpoint_default(client: TestClient):
    """Kiểm tra API GET /api/v1/market/matrix-10d trả về đủ 10 mã mặc định."""
    resp = client.get("/api/v1/market/matrix-10d")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "count" in data
    assert data["count"] == 10
    assert len(data["items"]) == 10


def test_get_matrix_10d_custom_params(client: TestClient):
    """Kiểm tra API GET /api/v1/market/matrix-10d với danh sách mã và số ngày tùy biến."""
    resp = client.get("/api/v1/market/matrix-10d?symbols=FPT,HPG&days=7")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 2
    assert len(data["items"]) == 2
    symbols = [it["symbol"] for it in data["items"]]
    assert set(symbols) == {"FPT", "HPG"}


def test_market_matrix_alias_routes(client: TestClient):
    """Đảm bảo các alias routes (/api/market/matrix-10d, /market/matrix-10d) hoạt động đồng nhất."""
    resp1 = client.get("/api/market/matrix-10d?symbols=FPT")
    resp2 = client.get("/market/matrix-10d?symbols=FPT")
    assert resp1.status_code == 200 and resp2.status_code == 200
    assert resp1.json()["items"][0]["symbol"] == "FPT"
    assert resp2.json()["items"][0]["symbol"] == "FPT"


# ==============================================================================
# 3. Single Source of Truth (SSOT) & Đồng Bộ Giá Tests
# ==============================================================================

def test_shared_price_source_cache_between_agent_and_service(real_deps):
    """Đảm bảo PriceAgent và MarketService dùng chung bộ đệm giá (Single Source of Truth)."""
    from backend.agents.price_agent import run_price_agent

    # 1. PriceAgent nạp giá FPT
    res_agent = run_price_agent("FPT", real_deps.price_source)
    if res_agent.error:
        pytest.skip("vnstock không khả dụng")

    # 2. MarketService lấy giá gần nhất
    ms = MarketService(price_source=real_deps.price_source)
    matrix = ms.get_matrix_10d(symbols=["FPT"], days=1)
    assert len(matrix) >= 1
    item = matrix[0]

    # Giá đóng cửa hiện tại giữa Chat PriceAgent và Market Watch phải trùng khớp 100%
    assert item["current_price"] == res_agent.latest_close
    assert round(item["change_pct"], 2) == round(res_agent.change_pct, 2)


# ==============================================================================
# 4. Phase 3.1: PriceAgent Trading Bands & Matrix 10D Sparkline Tests
# ==============================================================================

def test_phase3_price_agent_trading_bands_and_percentage_calculation():
    """Phase 3.1: Kiểm tra tính toán % thay đổi, giá tham chiếu, giá trần (+7%) và giá sàn (-7%)."""
    from backend.agents.price_agent.schemas import PriceAgentResult
    from backend.agents.price_agent.nodes import _from_quote
    from backend.domain.ports import PriceQuote

    # 1. Trường hợp bình thường (FPT tăng giá)
    quote_up = PriceQuote(symbol="FPT", latest_close=107.0, prev_close=100.0, error=None)
    res_up = _from_quote("FPT", quote_up)
    assert res_up.symbol == "FPT"
    assert res_up.latest_close == 107.0
    assert res_up.prev_close == 100.0
    assert res_up.change_pct is not None
    assert round(res_up.change_pct, 2) == 7.0
    assert res_up.reference_price == 100.0
    assert res_up.ceiling_price == 107.0
    assert res_up.floor_price == 93.0
    assert res_up.error is None

    # 2. Trường hợp giảm giá (HPG giảm)
    quote_down = PriceQuote(symbol="HPG", latest_close=25.0, prev_close=26.0, error=None)
    res_down = _from_quote("HPG", quote_down)
    assert res_down.change_pct is not None
    assert round(res_down.change_pct, 2) == -3.85
    assert res_down.reference_price == 26.0
    assert res_down.ceiling_price == round(26.0 * 1.07, 2)
    assert res_down.floor_price == round(26.0 * 0.93, 2)

    # 3. Trường hợp lỗi hoặc thiếu giá phiên trước
    quote_err = PriceQuote(symbol="XYZ", latest_close=None, prev_close=None, error="Lỗi sàn")
    res_err = _from_quote("XYZ", quote_err)
    assert res_err.change_pct is None
    assert res_err.ceiling_price is None
    assert res_err.floor_price is None
    assert res_err.error is not None


def test_phase3_market_matrix_10d_sparkline_and_fallback(client: TestClient):
    """Phase 3.1: Kiểm tra ma trận 10D VN30 đầy đủ sparklines, volumes và cơ chế fallback an toàn."""
    # 1. Gọi API /api/v1/market/matrix-10d
    resp = client.get("/api/v1/market/matrix-10d?days=10")
    assert resp.status_code == 200
    data = resp.json()

    assert data["count"] == 10
    assert len(data["items"]) == 10

    for item in data["items"]:
        # Kiểm tra đủ các trường theo đặc tả
        assert "symbol" in item and item["symbol"] in DEFAULT_MARKET_SYMBOLS
        assert "current_price" in item and item["current_price"] > 0
        assert "change_pct" in item
        assert "total_volume" in item and item["total_volume"] >= 0
        assert "sparkline" in item
        assert len(item["sparkline"]) == 10, f"Mã {item['symbol']} phải có đủ 10 điểm sparkline"
        assert "sessions" in item
        assert len(item["sessions"]) == 10, f"Mã {item['symbol']} phải có đủ 10 sessions"

        # Kiểm tra cấu trúc session
        first_session = item["sessions"][0]
        assert "date" in first_session
        assert "close" in first_session and first_session["close"] > 0
        assert "open" in first_session
        assert "high" in first_session
        assert "low" in first_session
        assert "volume" in first_session

    # 2. Kiểm tra cơ chế fallback của VnstockPriceSource khi bật fallback_on_error
    class OfflineQuoteFactory:
        def __init__(self, symbol, source):
            pass
        def history(self, **kwargs):
            raise ConnectionError("Mạng ngoài ngắt kết nối")

    offline_src = VnstockPriceSource(quote_factory=OfflineQuoteFactory, fallback_on_error=True)
    fallback_quote = offline_src.fetch_latest_close("FPT")
    assert fallback_quote.error is None
    assert fallback_quote.latest_close is not None
    assert fallback_quote.latest_close > 0

    fallback_history = offline_src.fetch_history("FPT", days=10)
    assert len(fallback_history) == 10
    assert fallback_history[-1].close == fallback_quote.latest_close

