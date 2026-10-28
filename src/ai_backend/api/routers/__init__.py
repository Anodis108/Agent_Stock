"""Routers for AI Backend Microservice."""

from ai_backend.api.routers import chat, concepts, health, scan, v1
from ai_backend.api.routers.chat import router as chat_router
from ai_backend.api.routers.concepts import router as concepts_router
from ai_backend.api.routers.health import router as health_router
from ai_backend.api.routers.scan import router as scan_router

__all__ = [
    "chat",
    "concepts",
    "health",
    "scan",
    "v1",
    "chat_router",
    "concepts_router",
    "health_router",
    "scan_router",
]
