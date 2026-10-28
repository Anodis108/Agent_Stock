"""Symbol Scan Router for Web Backend."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from common.logging.logger import correlation_id_ctx, get_logger
from web_backend.api.deps import AppDeps, get_app_deps, get_current_user_id
from web_backend.api.helpers.validation import normalize_symbol
from web_backend.api.models.scan import ScanRequest, ScanResponse

logger = get_logger("web_backend.api.routers.scan")
router = APIRouter(tags=["scan"])

from web_backend.infra.ai_client.remote_ai_client import RemoteAiClient


@router.post(
    "/scan",
    response_model=ScanResponse,
    summary="Kích hoạt quét tín hiệu kỹ thuật các mã theo dõi",
)
@router.post(
    "/api/v1/scan",
    response_model=ScanResponse,
)
def post_scan(
    body: ScanRequest,
    deps: AppDeps = Depends(get_app_deps),
    user_id: str = Depends(get_current_user_id),
) -> ScanResponse:
    cleaned_symbols = [normalize_symbol(s) for s in body.symbols if s.strip()]
    client = RemoteAiClient()
    alerts: list[dict[str, Any]] = []

    for s in (cleaned_symbols or []):
        try:
            # request_id: CorrelationIdMiddleware sinh 1 lần ở biên web
            res = client.scan(symbol=s, user_id=user_id, request_id=correlation_id_ctx.get(), threshold_pct=body.threshold_pct)
            if res.get("alert"):
                alerts.append(res["alert"])
            elif res.get("alerts"):
                alerts.extend(res["alerts"])
        except Exception as exc:
            logger.warning(f"Scan symbol {s} failed: {exc}")

    return ScanResponse(alerts=alerts, count=len(alerts))
