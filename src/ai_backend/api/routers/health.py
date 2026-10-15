"""Health check router for AI Backend Microservice (Cổng 8001)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter

router = APIRouter(tags=["system"])


@router.get("/health", summary="Kiểm tra trạng thái hoạt động của AI Backend")
def health_check() -> dict[str, Any]:
    """Trả về trạng thái hoạt động của AI Engine, Swarm StateGraph và tài nguyên phụ trợ."""
    return {
        "status": "ok",
        "service": "ai_backend",
        "port": 8001,
        "swarm": "ready",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
