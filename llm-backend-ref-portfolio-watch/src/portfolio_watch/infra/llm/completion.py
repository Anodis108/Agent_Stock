"""Chat completion helpers — text, stream, parsed, tools."""

from __future__ import annotations

from collections.abc import Iterator
from typing import TypeVar

from openai.types.chat import ChatCompletion, ChatCompletionMessageParam
from pydantic import BaseModel

from src.portfolio_watch.infra.llm.client import get_client, mark_current_key_limited
from src.portfolio_watch.infra.llm.params import GenerationParams
from src.portfolio_watch.infra.llm.resilience import retry_with_backoff
from src.portfolio_watch.shared.settings import settings

TModel = TypeVar("TModel", bound=BaseModel)
Messages = list[ChatCompletionMessageParam]


def chat(messages: Messages, params: GenerationParams | None = None) -> str:
    params = params or GenerationParams()
    client = get_client()

    def _call() -> ChatCompletion:
        return client.chat.completions.create(
            model=settings.llm_model,
            messages=messages,
            **params.to_openai_kwargs(),
        )

    response = retry_with_backoff(
        _call,
        max_retries=settings.llm_max_retries,
        on_rate_limit=lambda: mark_current_key_limited(client),
    )
    return response.choices[0].message.content or ""


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
    client = get_client()

    def _call():
        return client.chat.completions.parse(
            model=settings.llm_model,
            messages=messages,
            response_format=schema,
            **params.to_openai_kwargs(),
        )

    completion = retry_with_backoff(
        _call,
        max_retries=settings.llm_max_retries,
        on_rate_limit=lambda: mark_current_key_limited(client),
    )
    parsed = completion.choices[0].message.parsed
    if parsed is None:
        raise ValueError("Model không trả về output khớp schema.")
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

    return retry_with_backoff(
        _call,
        max_retries=settings.llm_max_retries,
        on_rate_limit=lambda: mark_current_key_limited(client),
    )


# Structured output helpers (Phase 6)
from src.portfolio_watch.infra.llm.structured import (
    call_llm_structured,
    extract_json_str,
    parse_structured,
)

