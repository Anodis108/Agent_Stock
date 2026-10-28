"""Chat completion — text, stream, parsed, tools (thin layer on OpenAI SDK)."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any, TypeVar

from openai.types.chat import ChatCompletion, ChatCompletionMessageParam
from pydantic import BaseModel

from ai_backend.infra.cost.tracker import check_budget_or_raise
from ai_backend.infra.llm.async_client import iter_sync_astream
from ai_backend.infra.llm.client import get_client, mark_current_key_limited
from ai_backend.infra.llm.params import GenerationParams
from ai_backend.infra.llm.providers import (
    call_with_backend_fallback,
    call_with_model_cascade,
    resolve_model_chain,
)
from ai_backend.infra.llm.resilience import retry_with_backoff
from common.settings import settings

TModel = TypeVar("TModel", bound=BaseModel)
Messages = list[ChatCompletionMessageParam]


def _record_usage(response: Any, *, model: str) -> None:
    if not hasattr(response, "usage") or not response.usage:
        return
    try:
        from ai_backend.infra.cost.tracker import record_completion_usage

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
    cached = _try_tiered_cache_get(primary_model)
    if cached is not None:
        _on_cache_hit(primary_model)
        return cached

    cache_key, cache = _resolve_exact_cache_key(primary_model)
    from ai_backend.infra.llm.semaphore import llm_semaphore_slot

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

    content = call_with_model_cascade(
        models,
        lambda resolved: call_with_backend_fallback(
            lambda backend: _call_one(resolved, backend)
        ),
    )
    _store_tiered_cache(cache_key, cache, content)
    return content


def chat_stream(
    messages: Messages,
    params: GenerationParams | None = None,
    *,
    model: str | None = None,
) -> Iterator[str]:
    """Streaming — yield từng token (AsyncOpenAI qua iter_sync_astream)."""
    params = params or GenerationParams()
    check_budget_or_raise()
    resolved_model = resolve_model_chain(model)[0]
    cache_key, cache = _resolve_exact_cache_key(resolved_model)
    if cache_key is not None and cache is not None:
        cached = cache.get(cache_key)
        if cached is not None:
            _on_cache_hit(resolved_model)
            yield cached
            return

    collected: list[str] = []
    completed: list[bool] = []
    for token in iter_sync_astream(
        messages, params, model=model, stream_completed=completed
    ):
        collected.append(token)
        yield token

    if completed and cache_key is not None and cache is not None:
        cache.set(cache_key, "".join(collected))


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

    from ai_backend.infra.llm.semaphore import llm_semaphore_slot

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

    return call_with_model_cascade(
        models,
        lambda resolved: call_with_backend_fallback(
            lambda backend: _call_one(resolved, backend)
        ),
    )


def chat_with_tools(
    messages: Messages,
    tools: list[dict],
    params: GenerationParams | None = None,
    *,
    model: str | None = None,
) -> ChatCompletion:
    params = params or GenerationParams()
    check_budget_or_raise()
    resolved_model = resolve_model_chain(model)[0]
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


# --- Exact / semantic cache (cùng file, không tách completion_cache.py) ---


def _resolve_exact_cache_key(model: str) -> tuple[str, Any] | tuple[None, None]:
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


def _record_cache_hit_cost(*, model: str) -> None:
    try:
        from ai_backend.infra.cost.tracker import record_completion_usage

        record_completion_usage(
            model=model,
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            cache_hit=True,
        )
    except Exception:
        pass


def _try_tiered_cache_get(model: str) -> str | None:
    cache_key, cache = _resolve_exact_cache_key(model)
    if cache_key is not None and cache is not None:
        hit = cache.get(cache_key)
        if hit is not None:
            return hit
    try:
        from ai_backend.infra.cache.semantic import try_semantic_cache_get

        return try_semantic_cache_get()
    except Exception:
        return None


def _store_tiered_cache(cache_key: str | None, cache: Any, content: str) -> None:
    if cache_key is not None and cache is not None:
        cache.set(cache_key, content)
    try:
        from ai_backend.infra.cache.semantic import store_semantic_cache_entry

        store_semantic_cache_entry(content)
    except Exception:
        pass


def _on_cache_hit(model: str) -> None:
    _record_cache_hit_cost(model=model)


