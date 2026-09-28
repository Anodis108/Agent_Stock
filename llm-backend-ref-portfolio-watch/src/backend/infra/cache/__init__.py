"""LLM response cache — exact (Phase 8) and semantic (Phase 9)."""

from backend.infra.cache.exact import (
    ExactCache,
    clear_llm_cache_context,
    get_exact_cache,
    get_llm_cache_context,
    is_exact_cache_enabled,
    llm_cache_scope,
    make_cache_key,
    normalize_question,
    set_llm_cache_context,
)
from backend.infra.cache.semantic import (
    SemanticCache,
    clear_semantic_question,
    cosine_similarity,
    embed_question,
    get_semantic_cache,
    get_semantic_question,
    is_dynamic_question,
    is_semantic_cache_enabled,
    set_semantic_question,
    store_semantic_cache_entry,
    try_semantic_cache_get,
)

__all__ = [
    "ExactCache",
    "SemanticCache",
    "clear_llm_cache_context",
    "clear_semantic_question",
    "cosine_similarity",
    "embed_question",
    "get_exact_cache",
    "get_llm_cache_context",
    "get_semantic_cache",
    "get_semantic_question",
    "is_dynamic_question",
    "is_exact_cache_enabled",
    "is_semantic_cache_enabled",
    "llm_cache_scope",
    "make_cache_key",
    "normalize_question",
    "set_llm_cache_context",
    "set_semantic_question",
    "store_semantic_cache_entry",
    "try_semantic_cache_get",
]
