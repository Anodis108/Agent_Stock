"""Chat completion helpers — text, stream, parsed, tools."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any, TypeVar

from openai.types.chat import ChatCompletion, ChatCompletionMessageParam
from pydantic import BaseModel

from backend.infra.llm.client import get_client, mark_current_key_limited
from backend.infra.llm.params import GenerationParams
from backend.infra.llm.resilience import retry_with_backoff
from backend.shared.settings import settings

TModel = TypeVar("TModel", bound=BaseModel)
Messages = list[ChatCompletionMessageParam]


def _resolve_exact_cache_key() -> tuple[str, Any] | tuple[None, None]:
    from backend.infra.cache.exact import (
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
        settings.llm_model,
        normalize_question(str(normalized_q)),
    )
    return key, cache


def _record_cache_hit_cost() -> None:
    try:
        from backend.infra.cost.tracker import record_completion_usage

        record_completion_usage(
            model=settings.llm_model,
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            cache_hit=True,
        )
    except Exception:
        pass


def _try_tiered_cache_get() -> str | None:
    cache_key, cache = _resolve_exact_cache_key()
    if cache_key is not None and cache is not None:
        hit = cache.get(cache_key)
        if hit is not None:
            return hit
    try:
        from backend.infra.cache.semantic import try_semantic_cache_get

        return try_semantic_cache_get()
    except Exception:
        return None


def _store_tiered_cache(cache_key: str | None, cache: Any, content: str) -> None:
    if cache_key is not None and cache is not None:
        cache.set(cache_key, content)
    try:
        from backend.infra.cache.semantic import store_semantic_cache_entry

        store_semantic_cache_entry(content)
    except Exception:
        pass


def chat(messages: Messages, params: GenerationParams | None = None) -> str:
    params = params or GenerationParams()
    cache_key, cache = _resolve_exact_cache_key()
    cached = _try_tiered_cache_get()
    if cached is not None:
        _record_cache_hit_cost()
        return cached

    from backend.infra.llm.semaphore import llm_semaphore_slot

    client = get_client()

    def _call() -> ChatCompletion:
        return client.chat.completions.create(
            model=settings.llm_model,
            messages=messages,
            **params.to_openai_kwargs(),
        )

    with llm_semaphore_slot():
        response = retry_with_backoff(
            _call,
            max_retries=settings.llm_max_retries,
            on_rate_limit=lambda: mark_current_key_limited(client),
        )
    content = response.choices[0].message.content or ""
    _store_tiered_cache(cache_key, cache, content)
    if hasattr(response, "usage") and response.usage:
        try:
            from backend.infra.monitoring.tracing import record_step_usage

            record_step_usage(
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
                model=settings.llm_model,
            )
        except Exception:
            pass
        try:
            from backend.infra.cost.tracker import record_completion_usage

            record_completion_usage(
                model=settings.llm_model,
                prompt_tokens=response.usage.prompt_tokens or 0,
                completion_tokens=response.usage.completion_tokens or 0,
                total_tokens=response.usage.total_tokens,
                cache_hit=False,
            )
        except Exception:
            pass
    return content


def chat_stream(
    messages: Messages, params: GenerationParams | None = None
) -> Iterator[str]:
    params = params or GenerationParams()
    client = get_client()

    def _open_stream():
        return client.chat.completions.create(
            model=settings.llm_model,
            messages=messages,
            stream=True,
            **params.to_openai_kwargs(),
        )

    stream = retry_with_backoff(
        _open_stream,
        max_retries=settings.llm_max_retries,
        on_rate_limit=lambda: mark_current_key_limited(client),
    )

    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta


def chat_parsed(
    messages: Messages,
    schema: type[TModel],
    params: GenerationParams | None = None,
) -> TModel:
    params = params or GenerationParams()
    cache_key, cache = _resolve_exact_cache_key()
    if cache_key is not None and cache is not None:
        hit = cache.get(cache_key)
        if hit is not None:
            _record_cache_hit_cost()
            return schema.model_validate_json(hit)

    from backend.infra.llm.semaphore import llm_semaphore_slot

    client = get_client()

    def _call():
        return client.chat.completions.parse(
            model=settings.llm_model,
            messages=messages,
            response_format=schema,
            **params.to_openai_kwargs(),
        )

    with llm_semaphore_slot():
        completion = retry_with_backoff(
            _call,
            max_retries=settings.llm_max_retries,
            on_rate_limit=lambda: mark_current_key_limited(client),
        )
    if hasattr(completion, "usage") and completion.usage:
        try:
            from backend.infra.monitoring.tracing import record_step_usage

            record_step_usage(
                prompt_tokens=completion.usage.prompt_tokens,
                completion_tokens=completion.usage.completion_tokens,
                total_tokens=completion.usage.total_tokens,
                model=settings.llm_model,
            )
        except Exception:
            pass
        try:
            from backend.infra.cost.tracker import record_completion_usage

            record_completion_usage(
                model=settings.llm_model,
                prompt_tokens=completion.usage.prompt_tokens or 0,
                completion_tokens=completion.usage.completion_tokens or 0,
                total_tokens=completion.usage.total_tokens,
                cache_hit=False,
            )
        except Exception:
            pass
    parsed = completion.choices[0].message.parsed
    if parsed is None:
        raise ValueError("Model không trả về output khớp schema.")
    _store_tiered_cache(cache_key, cache, parsed.model_dump_json())
    return parsed


def chat_with_tools(
    messages: Messages,
    tools: list[dict],
    params: GenerationParams | None = None,
) -> ChatCompletion:
    params = params or GenerationParams()
    client = get_client()

    def _call() -> ChatCompletion:
        return client.chat.completions.create(
            model=settings.llm_model,
            messages=messages,
            tools=tools,
            **params.to_openai_kwargs(),
        )

    response = retry_with_backoff(
        _call,
        max_retries=settings.llm_max_retries,
        on_rate_limit=lambda: mark_current_key_limited(client),
    )
    if hasattr(response, "usage") and response.usage:
        try:
            from backend.infra.monitoring.tracing import record_step_usage

            record_step_usage(
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
                model=settings.llm_model,
            )
        except Exception:
            pass
        try:
            from backend.infra.cost.tracker import record_completion_usage

            record_completion_usage(
                model=settings.llm_model,
                prompt_tokens=response.usage.prompt_tokens or 0,
                completion_tokens=response.usage.completion_tokens or 0,
                total_tokens=response.usage.total_tokens,
            )
        except Exception:
            pass
    return response


# Structured output helpers (Phase 6)
from backend.infra.llm.structured import (
    call_llm_structured,
    extract_json_str,
    parse_structured,
)

