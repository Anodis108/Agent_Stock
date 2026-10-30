"""Chat completion — Bài 1, Section 1 (Chat Completions) + 5 (Function Calling) + 6 (Streaming).

Lớp mỏng trên OpenAI SDK gom 4 cách gọi model mà Bài 1 dạy:
  - chat()            : gọi cơ bản, trả text.
  - chat_stream()     : streaming, yield từng token.
  - chat_parsed()     : structured output với Pydantic (Section 4).
  - chat_with_tools() : function calling, trả về tool_calls để code thực thi (Section 5).

Mọi lời gọi đều bọc trong retry_with_backoff + key rotation (Section 6).

vn-stock: kiểm tra budget trước mỗi lời gọi; `model` có thể override settings.
Cache và ghi usage không nằm ở đây — caller dùng `infra.cache.tiered` (giống demo:
route/script bọc quanh `chat` / `chat_with_usage`, không nhét vào hàm chat).
`chat_stream` = SDK sync như demo (LangGraph sync node). Async stream → `async_client.astream_chat`.
Agent structured output → `chat_parsed()` (giống demo). LangGraph ReAct → `client.base_llm()`.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import TypeVar

from openai.types import CompletionUsage
from openai.types.chat import ChatCompletion, ChatCompletionMessageParam
from pydantic import BaseModel

from ai_backend.infra.cost.tracker import check_budget_or_raise
from ai_backend.infra.llm.client import get_client, mark_current_key_limited
from ai_backend.infra.llm.params import GenerationParams
from ai_backend.infra.llm.resilience import retry_with_backoff
from common.settings import settings

TModel = TypeVar("TModel", bound=BaseModel)

Messages = list[ChatCompletionMessageParam]


def _resolved_model(model: str | None) -> str:
    return (model or settings.llm_model).strip() or settings.llm_model


def chat_with_usage(
    messages: Messages,
    params: GenerationParams | None = None,
    *,
    model: str | None = None,
) -> tuple[str, CompletionUsage | None]:
    """Như chat(), nhưng trả kèm usage thật để caller ghi cost (demo: cascade / cost replay)."""
    params = params or GenerationParams()
    check_budget_or_raise()
    resolved_model = _resolved_model(model)
    client = get_client()

    def _call() -> ChatCompletion:
        return client.chat.completions.create(
            model=resolved_model,
            messages=messages,
            **params.to_openai_kwargs(),
        )

    response = retry_with_backoff(
        _call,
        max_retries=settings.llm_max_retries,
        on_rate_limit=lambda: mark_current_key_limited(client),
    )
    return response.choices[0].message.content or "", response.usage


def chat(
    messages: Messages,
    params: GenerationParams | None = None,
    *,
    model: str | None = None,
) -> str:
    """Gọi chat completion cơ bản, trả về nội dung text của assistant.

    Section 1: chat.completions.create(messages) -> assistant message.
    """
    text, _usage = chat_with_usage(messages, params, model=model)
    return text


def chat_stream(
    messages: Messages,
    params: GenerationParams | None = None,
    *,
    model: str | None = None,
) -> Iterator[str]:
    """Streaming — yield từng đoạn token ngay khi model sinh ra (Section 6).

    Lưu ý: stream không retry giữa chừng (một khi đã bắt đầu nhận token).
    Backoff chỉ áp dụng cho bước khởi tạo stream.
    """
    params = params or GenerationParams()
    check_budget_or_raise()

    resolved_model = _resolved_model(model)
    client = get_client()

    def _open():
        return client.chat.completions.create(
            model=resolved_model,
            messages=messages,
            stream=True,
            **params.to_openai_kwargs(),
        )

    stream = retry_with_backoff(
        _open,
        max_retries=settings.llm_max_retries,
        on_rate_limit=lambda: mark_current_key_limited(client),
    )

    for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta


def chat_parsed_with_usage(
    messages: Messages,
    schema: type[TModel],
    params: GenerationParams | None = None,
    *,
    model: str | None = None,
) -> tuple[TModel, CompletionUsage | None]:
    """Như chat_parsed(), nhưng trả kèm usage để caller ghi cost."""
    params = params or GenerationParams()
    check_budget_or_raise()

    resolved_model = _resolved_model(model)
    client = get_client()

    def _call() -> ChatCompletion:
        return client.chat.completions.parse(
            model=resolved_model,
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
    return parsed, completion.usage


def chat_parsed(
    messages: Messages,
    schema: type[TModel],
    params: GenerationParams | None = None,
    *,
    model: str | None = None,
) -> TModel:
    """Structured output — ép model trả về đúng schema Pydantic (Section 4).

    Dùng client.chat.completions.parse() (đã ra khỏi beta).
    """
    parsed, _usage = chat_parsed_with_usage(messages, schema, params, model=model)
    return parsed


def chat_with_tools(
    messages: Messages,
    tools: list[dict],
    params: GenerationParams | None = None,
    *,
    model: str | None = None,
) -> ChatCompletion:
    """Function calling — trả về response thô để code kiểm tra tool_calls (Section 5).

    Trả nguyên ChatCompletion (không rút gọn về text) vì caller cần đọc
    finish_reason và message.tool_calls để quyết định thực thi function nào.
    """
    params = params or GenerationParams()
    check_budget_or_raise()

    resolved_model = _resolved_model(model)
    client = get_client()

    def _call() -> ChatCompletion:
        return client.chat.completions.create(
            model=resolved_model,
            messages=messages,
            tools=tools,
            **params.to_openai_kwargs(),
        )

    return retry_with_backoff(
        _call,
        max_retries=settings.llm_max_retries,
        on_rate_limit=lambda: mark_current_key_limited(client),
    )
