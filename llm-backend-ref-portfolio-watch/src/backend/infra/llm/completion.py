"""Chat completion helpers — text, stream, parsed, tools."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any, TypeVar

from openai.types.chat import ChatCompletion, ChatCompletionMessageParam
from pydantic import BaseModel

from backend.infra.cost.tracker import check_budget_or_raise
from backend.infra.llm.client import get_client, mark_current_key_limited
from backend.infra.llm.params import GenerationParams
from backend.infra.llm.providers import (
    call_with_backend_fallback,
    call_with_model_cascade,
    resolve_model_chain,
)
from backend.infra.llm.resilience import retry_with_backoff
from backend.shared.settings import settings

TModel = TypeVar("TModel", bound=BaseModel)
Messages = list[ChatCompletionMessageParam]


def _resolve_exact_cache_key(model: str) -> tuple[str, Any] | tuple[None, None]:
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
        model,
        normalize_question(str(normalized_q)),
    )
    return key, cache


def _record_cache_hit_cost(*, model: str) -> None:
    try:
        from backend.infra.cost.tracker import record_completion_usage

        record_completion_usage(
            model=model,
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            cache_hit=True,
        )
    except Exception:
        pass


def _try_tiered_cache_get() -> str | None:
    cache_key, cache = _resolve_exact_cache_key(settings.llm_model)
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


def _record_usage(response: Any, *, model: str) -> None:
    if not hasattr(response, "usage") or not response.usage:
        return
    try:
        from backend.infra.monitoring.tracing import record_step_usage

        record_step_usage(
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
            total_tokens=response.usage.total_tokens,
            model=model,
        )
    except Exception:
        pass
    try:
        from backend.infra.cost.tracker import record_completion_usage

        record_completion_usage(
            model=model,
            prompt_tokens=response.usage.prompt_tokens or 0,
            completion_tokens=response.usage.completion_tokens or 0,
            total_tokens=response.usage.total_tokens,
            cache_hit=False,
        )
    except Exception:
        pass


def chat(
    messages: Messages,
    params: GenerationParams | None = None,
    *,
    model: str | None = None,
) -> str:
    params = params or GenerationParams()
    check_budget_or_raise()
    models = resolve_model_chain(model)
    primary_model = models[0]
    cache_key, cache = _resolve_exact_cache_key(primary_model)
    cached = _try_tiered_cache_get()
    if cached is not None:
        _record_cache_hit_cost(model=primary_model)
        return cached

    from backend.infra.llm.semaphore import llm_semaphore_slot

    def _call_one(resolved_model: str, backend_name: str | None) -> str:
        client = get_client() if backend_name is None else get_client(backend_name)

        def _call() -> ChatCompletion:
            return client.chat.completions.create(
                model=resolved_model,
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
        _record_usage(response, model=resolved_model)
        return content

    def _call_model(resolved_model: str) -> str:
        return call_with_backend_fallback(
            lambda backend: _call_one(resolved_model, backend)
        )

    content = call_with_model_cascade(models, _call_model)
    _store_tiered_cache(cache_key, cache, content)
    return content


def chat_stream(
    messages: Messages,
    params: GenerationParams | None = None,
    *,
    model: str | None = None,
) -> Iterator[str]:
    params = params or GenerationParams()
    check_budget_or_raise()
    models = resolve_model_chain(model)
    resolved_model = models[0]
    client = get_client()

    def _open_stream():
        return client.chat.completions.create(
            model=resolved_model,
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
    *,
    model: str | None = None,
) -> TModel:
    params = params or GenerationParams()
    check_budget_or_raise()
    models = resolve_model_chain(model)
    primary_model = models[0]
    cache_key, cache = _resolve_exact_cache_key(primary_model)
    if cache_key is not None and cache is not None:
        hit = cache.get(cache_key)
        if hit is not None:
            _record_cache_hit_cost(model=primary_model)
            return schema.model_validate_json(hit)

    from backend.infra.llm.semaphore import llm_semaphore_slot

    def _call_one(resolved_model: str, backend_name: str | None) -> TModel:
        client = get_client() if backend_name is None else get_client(backend_name)

        def _call():
            return client.chat.completions.parse(
                model=resolved_model,
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
        _record_usage(completion, model=resolved_model)
        parsed = completion.choices[0].message.parsed
        if parsed is None:
            raise ValueError("Model không trả về output khớp schema.")
        _store_tiered_cache(cache_key, cache, parsed.model_dump_json())
        return parsed

    def _call_model(resolved_model: str) -> TModel:
        return call_with_backend_fallback(
            lambda backend: _call_one(resolved_model, backend)
        )

    return call_with_model_cascade(models, _call_model)


def chat_with_tools(
    messages: Messages,
    tools: list[dict],
    params: GenerationParams | None = None,
    *,
    model: str | None = None,
) -> ChatCompletion:
    params = params or GenerationParams()
    check_budget_or_raise()
    models = resolve_model_chain(model)
    resolved_model = models[0]
    client = get_client()

    def _call() -> ChatCompletion:
        return client.chat.completions.create(
            model=resolved_model,
            messages=messages,
            tools=tools,
            **params.to_openai_kwargs(),
        )

    response = retry_with_backoff(
        _call,
        max_retries=settings.llm_max_retries,
        on_rate_limit=lambda: mark_current_key_limited(client),
    )
    _record_usage(response, model=resolved_model)
    return response


# Structured output helpers (Phase 6)
from backend.infra.llm.structured import (
    call_llm_structured,
    extract_json_str,
    parse_structured,
)
