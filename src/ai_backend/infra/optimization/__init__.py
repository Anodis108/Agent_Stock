"""Production optimization — map `app/optimization/` (Module III Bài 8)."""

from ai_backend.infra.optimization.caching import (
    get_exact_cache,
    is_exact_cache_enabled,
    try_semantic_cache_get,
)
from ai_backend.infra.optimization.routing import (
    call_with_backend_fallback,
    call_with_model_cascade,
    resolve_model_chain,
)

__all__ = [
    "call_with_backend_fallback",
    "call_with_model_cascade",
    "get_exact_cache",
    "is_exact_cache_enabled",
    "resolve_model_chain",
    "try_semantic_cache_get",
]
