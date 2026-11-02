"""Production optimization — map `app/optimization/` (Module III Bài 8)."""

from ai_backend.infra.optimization.caching import (
    get_exact_cache,
    is_exact_cache_enabled,
    try_semantic_cache_get,
)

__all__ = [
    "get_exact_cache",
    "is_exact_cache_enabled",
    "try_semantic_cache_get",
]
