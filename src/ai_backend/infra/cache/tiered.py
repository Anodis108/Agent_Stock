"""Cache hai tầng + ghi usage — caller bọc quanh completion, không nhét vào chat().

Giống demo: route (`routes_chat`) và script cost replay tự peek/store và
`record` usage. `chat` / `chat_stream` / `chat_parsed` chỉ gọi model.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any, TypeVar

from pydantic import BaseModel

from ai_backend.infra.cost.tracker import (
    check_budget_or_raise,
    record_cache_hit,
    record_response_usage,
)
from ai_backend.infra.llm.params import GenerationParams
from common.settings import settings

TModel = TypeVar("TModel", bound=BaseModel)


def _model(model: str | None) -> str:
    return (model or settings.llm_model).strip() or settings.llm_model


def resolve_exact_cache_key(model: str) -> tuple[str, Any] | tuple[None, None]:
    from ai_backend.infra.cache.exact import (
        get_exact_cache,
        get_llm_cache_context,
        is_exact_cache_enabled,
        normalize_question,
    )

    if not is_exact_cache_enabled():
        return None, None
    ctx = get_llm_cache_context()
    prompt_name = ctx.get("prompt_name")
    normalized_q = ctx.get("normalized_question")
    if not prompt_name or normalized_q is None:
        return None, None
    prompt_version = str(ctx.get("prompt_version") or "production")
    cache = get_exact_cache()
    key = cache.make_key(
        prompt_name,
        prompt_version,
        model,
        normalize_question(str(normalized_q)),
    )
    return key, cache


def try_tiered_cache_get(model: str) -> str | None:
    """Exact trước, semantic sau. Semantic lỗi → coi như miss."""
    cache_key, cache = resolve_exact_cache_key(model)
    if cache_key is not None and cache is not None:
        hit = cache.get(cache_key)
        if hit is not None:
            return hit
    try:
        from ai_backend.infra.cache.semantic import try_semantic_cache_get

        return try_semantic_cache_get()
    except Exception:
        return None


def store_tiered_cache(model: str, content: str) -> None:
    cache_key, cache = resolve_exact_cache_key(model)
    if cache_key is not None and cache is not None:
        cache.set(cache_key, content)
    try:
        from ai_backend.infra.cache.semantic import store_semantic_cache_entry

        store_semantic_cache_entry(content)
    except Exception:
        pass


def chat_cached(
    messages: list,
    params: GenerationParams | None = None,
    *,
    model: str | None = None,
) -> str:
    """Exact rồi semantic; miss thì gọi model, ghi usage, lưu cả hai tầng."""
    from ai_backend.infra.llm.completion import chat_with_usage

    check_budget_or_raise()
    resolved = _model(model)
    cached = try_tiered_cache_get(resolved)
    if cached is not None:
        record_cache_hit(model=resolved)
        return cached

    text, usage = chat_with_usage(messages, params, model=model)
    record_response_usage(usage, model=resolved)
    store_tiered_cache(resolved, text)
    return text


def chat_stream_cached(
    messages: list,
    params: GenerationParams | None = None,
    *,
    model: str | None = None,
) -> Iterator[str]:
    """Stream chỉ dùng exact cache (semantic không áp cho từng token)."""
    from ai_backend.infra.llm.completion import chat_stream

    check_budget_or_raise()
    resolved = _model(model)
    cache_key, cache = resolve_exact_cache_key(resolved)
    if cache_key is not None and cache is not None:
        hit = cache.get(cache_key)
        if hit is not None:
            record_cache_hit(model=resolved)
            yield hit
            return

    collected: list[str] = []
    try:
        for delta in chat_stream(messages, params, model=model):
            collected.append(delta)
            yield delta
    except Exception:
        raise
    else:
        if cache_key is not None and cache is not None:
            cache.set(cache_key, "".join(collected))


def chat_parsed_cached(
    messages: list,
    schema: type[TModel],
    params: GenerationParams | None = None,
    *,
    model: str | None = None,
) -> TModel:
    """Exact rồi semantic; hit thì parse JSON đã lưu. Miss thì gọi model và lưu JSON."""
    from ai_backend.infra.llm.completion import chat_parsed_with_usage

    check_budget_or_raise()
    resolved = _model(model)
    cached = try_tiered_cache_get(resolved)
    if cached is not None:
        record_cache_hit(model=resolved)
        return schema.model_validate_json(cached)

    parsed, usage = chat_parsed_with_usage(messages, schema, params, model=model)
    record_response_usage(usage, model=resolved)
    store_tiered_cache(resolved, parsed.model_dump_json())
    return parsed
