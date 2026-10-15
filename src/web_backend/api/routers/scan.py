"""Symbol Scan Router for Web Backend."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from common.logging.logger import get_logger
from web_backend.api.deps import AppDeps, get_app_deps
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
) -> ScanResponse:
    cleaned_symbols = [normalize_symbol(s) for s in body.symbols if s.strip()]
    client = RemoteAiClient()
    alerts: list[dict[str, Any]] = []

    for s in (cleaned_symbols or []):
        try:
            res = client.scan(symbol=s, threshold_pct=body.threshold_pct)
            if res.get("alert"):
                alerts.append(res["alert"])
            elif res.get("alerts"):
                alerts.extend(res["alerts"])
        except Exception as exc:
            logger.warning(f"Scan symbol {s} failed: {exc}")

    return ScanResponse(alerts=alerts, count=len(alerts))
