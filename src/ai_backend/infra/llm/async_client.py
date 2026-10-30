"""Async LLM client — Module III, Bài 4, Section 4 (FastAPI Patterns cho LLM).

Vì sao cần file này khi đã có client.py (sync)?
  Bài học Section 4 cảnh báo rõ: "đừng gọi SDK sync trong endpoint async (block
  event loop)". `client.py` trả `OpenAI` (sync) và `resilience.retry_with_backoff`
  dùng `time.sleep()` — cả hai đều CHẶN event loop nếu gọi từ `async def`.
  File này là bản async tương ứng: `AsyncOpenAI` + `asyncio.sleep()`.

3 pattern bài học yêu cầu, gom ở đây:
  1. Async client       — AsyncOpenAI, không block event loop.
  2. Backpressure       — Semaphore giới hạn số request LLM đồng thời; request
     thứ N+1 xếp hàng thay vì làm sập upstream/vượt rate limit.
  3. Retry có jitter    — exponential backoff + jitter cho 429/timeout, dùng
     `asyncio.sleep` (KHÔNG phải time.sleep).

Tái dùng key rotation của Bài 1 (`_api_key_for_backend`) — không viết lại logic chọn key.

LangGraph / `completion.chat_stream` dùng SDK sync (giống demo) — không qua file này.
Dùng `astream_chat` khi endpoint FastAPI async stream trực tiếp (tùy chọn).
"""

from __future__ import annotations

import asyncio
import random
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any

from openai import APITimeoutError, AsyncOpenAI, RateLimitError

from ai_backend.infra.llm.backends import get_backend
from ai_backend.infra.llm.client import _api_key_for_backend, _resolve_base_url
from ai_backend.infra.llm.params import GenerationParams
from common.settings import settings

# Section 4: giới hạn số lời gọi LLM ĐỒNG THỜI. Request thứ (N+1) sẽ `await`
# ở đây cho tới khi có slot — backpressure ở tầng app, không đẩy hết tải lên provider.
# Module level → dùng CHUNG mọi request trong 1 uvicorn worker (giống demo).
_LLM_SEMAPHORE = asyncio.Semaphore(settings.llm_max_concurrency)


def semaphore_state() -> dict[str, int]:
    """Số slot còn trống / tổng — `/health`, benchmark."""
    return {
        "limit": settings.llm_max_concurrency,
        "available": _LLM_SEMAPHORE._value,  # noqa: SLF001 — quan sát, không điều khiển
    }


def get_async_client() -> AsyncOpenAI:
    """AsyncOpenAI trỏ tới backend đang cấu hình — song song với `client.get_client()`.

    `max_retries=0`: TẮT retry tự động của SDK để tự quản backoff + jitter
    (bài học Section 4: SDK retry không có jitter, dễ gây thundering herd).
    """
    name = settings.llm_backend.strip().lower()
    backend = get_backend(name)
    return AsyncOpenAI(
        api_key=_api_key_for_backend(name),
        base_url=_resolve_base_url(backend.default_base_url),
        timeout=settings.llm_timeout_seconds,
        max_retries=0,
    )


async def acall_with_retry(
    fn: Callable[[], Awaitable[Any]],
    *,
    max_retries: int | None = None,
) -> Any:
    """Bản ASYNC của `resilience.retry_with_backoff` — `asyncio.sleep` thay `time.sleep`."""
    attempts = settings.llm_max_retries if max_retries is None else max_retries
    for attempt in range(attempts):
        try:
            return await fn()
        except (RateLimitError, APITimeoutError):
            if attempt == attempts - 1:
                raise
            # exp backoff + jitter, cap ở 16s (bài học: min(2**attempt, 16) + jitter)
            backoff = min(2**attempt, 16) + random.uniform(0, 1)
            await asyncio.sleep(backoff)
    raise RuntimeError("acall_with_retry: hết số lần thử")


async def astream_chat(
    messages: list[dict],
    params: GenerationParams | None = None,
) -> AsyncIterator[str]:
    """Stream token bất đồng bộ, có backpressure qua semaphore.

    Semaphore giữ slot TRONG SUỐT quá trình stream — vì 1 stream vẫn chiếm tài
    nguyên phía provider. Không dùng từ LangGraph sync node; xem `completion.chat_stream`.
    """
    params = params or GenerationParams()

    async with _LLM_SEMAPHORE:
        client = get_async_client()

        async def _open():
            return await client.chat.completions.create(
                model=settings.llm_model,
                messages=messages,
                stream=True,
                **params.to_openai_kwargs(),
            )

        stream = await acall_with_retry(_open)

        async for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta
