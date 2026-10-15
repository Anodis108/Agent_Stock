"""Routers for AI Backend Microservice."""

from ai_backend.api.routers import chat_stream, health, scan, v1
from ai_backend.api.routers.chat_stream import alias_router as chat_stream_alias_router
from ai_backend.api.routers.chat_stream import router as chat_stream_router
from ai_backend.api.routers.health import router as health_router
from ai_backend.api.routers.scan import alias_router as scan_alias_router
from ai_backend.api.routers.scan import router as scan_router

__all__ = [
    "chat_stream",
    "health",
    "scan",
    "v1",
    "chat_stream_router",
    "chat_stream_alias_router",
    "health_router",
    "scan_router",
    "scan_alias_router",
]
