"""Dependency injection wiring for AI Backend Microservice."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from common.logging.logger import get_logger

logger = get_logger("ai_backend.api.deps")


@dataclass
class AiDeps:
    """Dependencies được inject vào các router AI Backend."""
    swarm_orchestrator: Any = None
    symbol_scanner_service: Any = None
    concept_rag_service: Any = None
    price_source: Any = None
    news_source: Any = None
    qdrant_retriever: Any = None
    cache_store: Any = None
    cost_tracker: Any = None


_ai_deps_instance = AiDeps()


def get_ai_deps() -> AiDeps:
    """Lấy dependency container của AI Backend."""
    return _ai_deps_instance


def set_ai_deps(deps: AiDeps | None) -> None:
    """Cập nhật dependency container của AI Backend (cho testing và initialization)."""
    global _ai_deps_instance
    _ai_deps_instance = deps or AiDeps()


__all__ = ["AiDeps", "get_ai_deps", "set_ai_deps"]
