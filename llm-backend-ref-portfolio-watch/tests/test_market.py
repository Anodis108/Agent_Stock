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
