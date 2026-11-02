"""Health check router for AI Backend Microservice (Cổng 8001)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter

from ai_backend.shared.settings import ai_settings

router = APIRouter(tags=["system"])


@router.get("/health", summary="Kiểm tra trạng thái hoạt động của AI Backend")
def health_check() -> dict[str, Any]:
    """Trả về trạng thái hoạt động của AI Engine, Swarm StateGraph và tài nguyên phụ trợ."""
    db_mode = "postgresql" if ai_settings.database_url else "not_configured"

    qdrant_status = "in_memory_fallback"
    try:
        from ai_backend.infra.storage.long_term_memory import get_qdrant_client
        if get_qdrant_client() is not None:
            qdrant_status = "connected"
    except Exception:
        pass

    minio_status = "local_disk_fallback"
    try:
        from common.storage import get_chart_store
        store = get_chart_store()
        if store is not None and store.is_connected():
            minio_status = "connected"
    except Exception:
        pass

    from ai_backend.infra.llm.async_client import semaphore_state

    return {
        "status": "ok",
        "service": "ai_backend",
        "port": 8001,
        "swarm": "ready",
        "llm_async_semaphore": semaphore_state(),
        "dependencies": {
            "database": db_mode,
            "qdrant": qdrant_status,
            "storage": {
                "backend": ai_settings.chart_backend,
                "status": minio_status,
                "minio_endpoint": ai_settings.minio_endpoint if ai_settings.chart_backend == "minio" else None,
            },
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
