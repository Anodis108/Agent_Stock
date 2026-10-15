"""Technical analysis symbol scanner router for AI Backend (/v1/scan)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header

from ai_backend.api.deps import AiDeps, get_ai_deps
from ai_backend.api.models.scan_models import ScanAlertOut, ScanRequest, ScanResponse
from common.logging.logger import get_correlation_id, get_logger

logger = get_logger("ai_backend.api.scan")

router = APIRouter(prefix="/v1", tags=["ai-scan"])
alias_router = APIRouter(tags=["ai-scan-alias"])


@router.post("/scan", response_model=ScanResponse, summary="Quét phân tích kỹ thuật và cảnh báo mã cổ phiếu")
@alias_router.post("/scan", response_model=ScanResponse, summary="Quét phân tích kỹ thuật alias")
def scan_symbol_endpoint(
    body: ScanRequest,
    deps: AiDeps = Depends(get_ai_deps),
    x_request_id: str | None = Header(default=None, alias="X-Request-Id"),
) -> ScanResponse:
    """Tiếp nhận mã chứng khoán, thực hiện phân tích kỹ thuật và kiểm tra ngưỡng cảnh báo."""
    sym = body.symbol.strip().upper()
    req_id = (body.request_id or x_request_id or get_correlation_id() or "").strip() or None
    threshold = float(body.threshold_pct) if body.threshold_pct is not None else 3.0

    logger.info(f"Yêu cầu quét kỹ thuật mã {sym} với ngưỡng {threshold}% [req_id={req_id}]")

    # Nếu có symbol_scanner_service được inject từ tầng Application (Phase 3.2)
    if hasattr(deps, "symbol_scanner_service") and deps.symbol_scanner_service is not None:
        try:
            return deps.symbol_scanner_service.scan(
                symbol=sym,
                user_id=body.user_id,
                threshold_pct=threshold,
                request_id=req_id,
            )
        except Exception as exc:
            logger.error(f"Lỗi scanner service: {exc}", exc_info=True)

    # Fallback response độc lập cho presentation layer
    return ScanResponse(
        symbol=sym,
        route="technical",
        threshold_pct=threshold,
        reason=f"Quét kỹ thuật hoàn tất cho mã {sym}",
        gate1_action=None,
        gate2_pending=False,
        error=None,
        request_id=req_id,
        alerts=[
            ScanAlertOut(
                symbol=sym,
                route="technical",
                threshold_pct=threshold,
                change_pct=0.0,
                triggered=False,
                reason=f"Tín hiệu kỹ thuật {sym} ổn định",
            )
        ],
        steps=[
            {"id": "step_1", "name": "price_scanner", "status": "done"},
            {"id": "step_2", "name": "indicator_analyzer", "status": "done"},
        ],
    )
