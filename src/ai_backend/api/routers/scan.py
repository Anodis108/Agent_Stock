"""Technical analysis symbol scanner router for AI Backend (/v1/scan)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from ai_backend.api.models.scan_models import (
    ScanRequest,
    ScanResponse,
    ScanResumeRequest,
    ScanResumeResponse,
)
from ai_backend.application.scan_service import ScanResumeInput, ScanService
from ai_backend.shared.exceptions import ScanExecutionException
from ai_backend.shared.logging import get_logger

logger = get_logger("ai_backend.api.scan")

router = APIRouter(prefix="/v1", tags=["ai-scan"])


@router.post("/scan", response_model=ScanResponse, summary="Quét phân tích kỹ thuật và cảnh báo mã cổ phiếu")
def scan_symbol_endpoint(body: ScanRequest, request: Request) -> ScanResponse:
    """Tiếp nhận mã chứng khoán, thực hiện phân tích kỹ thuật và kiểm tra ngưỡng cảnh báo."""
    symbols = [s.strip().upper() for s in body.symbol if s.strip()]
    threshold = float(body.threshold_pct) if body.threshold_pct is not None else 3.0

    scanner: ScanService = request.app.state.scan_service
    try:
        return scanner.scan(
            symbol=symbols,
            user_id=body.user_id,
            threshold_pct=threshold,
            request_id=body.request_id,
        )
    except Exception as exc:
        # Báo lỗi rõ ràng thay vì trả kết quả "ổn định" giả -> người dùng không bị đánh lừa.
        logger.error(f"Lỗi scanner service: {exc}", exc_info=True)
        raise ScanExecutionException(", ".join(symbols), str(exc)) from exc


@router.post("/scan/resume", response_model=ScanResumeResponse, summary="HITL scan — duyệt/từ chối hành động rồi resume graph")
def scan_resume_endpoint(body: ScanResumeRequest, request: Request) -> ScanResumeResponse:
    """Graph scan đang dừng trước scan_tools (thread_id) → duyệt thì chạy tool, từ chối thì bỏ qua rồi chạy tiếp."""
    scanner: ScanService = request.app.state.scan_service
    try:
        out = scanner.resume(
            ScanResumeInput(thread_id=body.thread_id, approve=body.approve, reason=body.reason, user_id=body.user_id)
        )
    except ValueError as exc:  # thread không có hành động chờ duyệt
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ScanResumeResponse(**out.model_dump())
