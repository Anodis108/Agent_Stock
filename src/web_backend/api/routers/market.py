"""Market Status & Sessions Router for Web Backend."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from web_backend.api.deps import AppDeps, get_app_deps
from web_backend.api.models.market import (
    MarketMatrixItemOut,
    MarketMatrixResponse,
    MarketSessionOut,
)

router = APIRouter(prefix="/api/market", tags=["market"])

try:
    from web_backend.application.market_service import MarketService
except ImportError:
    MarketService = None



@router.get(
    "/sessions",
    response_model=list[MarketSessionOut],
    summary="Xem phiên giao dịch chứng khoán hiện tại",
)
def get_market_sessions() -> list[MarketSessionOut]:
    """Trả về trạng thái các phiên giao dịch trong ngày trên sàn HSX/HNX."""
    sessions = [
        MarketSessionOut(
            session_type="ATO",
            start_time="09:00",
            end_time="09:15",
            is_active=False,
            description="Phiên khớp lệnh định kỳ mở cửa",
        ),
        MarketSessionOut(
            session_type="CONTINUOUS_MORNING",
            start_time="09:15",
            end_time="11:30",
            is_active=False,
            description="Phiên khớp lệnh liên tục sáng",
        ),
        MarketSessionOut(
            session_type="INTERMISSION",
            start_time="11:30",
            end_time="13:00",
            is_active=False,
            description="Nghỉ trưa",
        ),
        MarketSessionOut(
            session_type="CONTINUOUS_AFTERNOON",
            start_time="13:00",
            end_time="14:30",
            is_active=False,
            description="Phiên khớp lệnh liên tục chiều",
        ),
        MarketSessionOut(
            session_type="ATC",
            start_time="14:30",
            end_time="14:45",
            is_active=False,
            description="Phiên khớp lệnh định kỳ đóng cửa",
        ),
        MarketSessionOut(
            session_type="CLOSED",
            start_time="15:00",
            end_time="09:00",
            is_active=True,
            description="Thị trường đóng cửa",
        ),
    ]
    return sessions


@router.get(
    "/matrix",
    response_model=MarketMatrixResponse,
    summary="Bảng ma trận thị trường tổng quan",
)
def get_market_matrix(
    deps: AppDeps = Depends(get_app_deps),
) -> MarketMatrixResponse:
    """Trả về dữ liệu ma trận thị trường tóm tắt các mã VN30 phổ biến."""
    sample_symbols = ["VNM", "FPT", "VIC", "HPG", "TCB"]
    items = []
    for sym in sample_symbols:
        items.append(
            MarketMatrixItemOut(
                symbol=sym,
                price=50.0,
                change_pct=0.0,
                rsi=50.0,
                signal="NEUTRAL",
            )
        )
    return MarketMatrixResponse(
        sessions=get_market_sessions(),
        items=items,
    )
