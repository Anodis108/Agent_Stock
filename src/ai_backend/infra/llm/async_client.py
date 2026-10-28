"""Async LLM client. chat_stream gọi module này.

AsyncOpenAI không chặn event loop của FastAPI. Retry dùng asyncio.sleep.
Semaphore asyncio lấy giới hạn từ biến môi trường LLM_MAX_CONCURRENCY.
Mọi lời gọi dùng chung một event loop để semaphore giới hạn được các stream chạy song song.
"""

from __future__ import annotations

import asyncio
import queue
import random
import threading
from collections.abc import AsyncIterator, Awaitable, Callable, Iterator
from contextlib import asynccontextmanager
from typing import Any

from openai import APITimeoutError, AsyncOpenAI, RateLimitError
from openai.types.chat import ChatCompletionMessageParam

from ai_backend.infra.llm.backends import get_backend
from ai_backend.infra.llm.client import _get_pool, mark_current_key_limited
from ai_backend.infra.llm.params import GenerationParams
from ai_backend.infra.llm.providers import resolve_backend_chain, resolve_model_chain
from common.settings import settings

Messages = list[ChatCompletionMessageParam]

_semaphore: asyncio.Semaphore | None = None
_semaphore_limit: int | None = None
_loop: asyncio.AbstractEventLoop | None = None
_loop_thread: threading.Thread | None = None
_loop_ready: threading.Event | None = None
_loop_guard = threading.Lock()


def ensure_llm_async_loop() -> asyncio.AbstractEventLoop:
    """Event loop nền cho chat_stream. LangGraph gọi stream từ thread khác."""
    global _loop, _loop_thread, _loop_ready
    with _loop_guard:
        if (
            _loop is not None
            and _loop_thread is not None
            and _loop_thread.is_alive()
        ):
            loop = _loop
            ready = _loop_ready
        else:
            loop = asyncio.new_event_loop()
            ready = threading.Event()

            def _run() -> None:
                asyncio.set_event_loop(loop)
                loop.call_soon(ready.set)
                loop.run_forever()

            thread = threading.Thread(target=_run, name="llm-async-loop", daemon=True)
            thread.start()
            _loop = loop
            _loop_thread = thread
            _loop_ready = ready
    if ready is None or not ready.wait(5):
        raise RuntimeError("Không khởi động được event loop của async client")
    return loop


def get_llm_async_semaphore() -> asyncio.Semaphore:
    global _semaphore, _semaphore_limit
    limit = max(1, int(settings.llm_max_concurrency))
    if _semaphore is None or _semaphore_limit != limit:
        _semaphore = asyncio.Semaphore(limit)
        _semaphore_limit = limit
    return _semaphore


def reset_async_semaphore_for_tests() -> None:
    global _semaphore, _semaphore_limit
    _semaphore = None
    _semaphore_limit = None


def async_semaphore_available() -> int:
    return get_llm_async_semaphore()._value


@asynccontextmanager
async def async_llm_slot() -> AsyncIterator[None]:
    sem = get_llm_async_semaphore()
    await sem.acquire()
    try:
        yield
    finally:
        sem.release()


def get_async_client(backend_name: str | None = None) -> AsyncOpenAI:
    name = (backend_name or settings.llm_backend).strip().lower()
    backend = get_backend(name)
    base_url = settings.llm_base_url or backend.default_base_url or None
    api_key = _get_pool().get_key() if backend.requires_real_key else backend.dummy_key
    return AsyncOpenAI(api_key=api_key, base_url=base_url, max_retries=0)


async def acall_with_retry(
    fn: Callable[[], Awaitable],
    *,
    max_retries: int | None = None,
):
    """Gọi fn. RateLimitError và APITimeoutError thì chờ rồi thử lại."""
    attempts = settings.llm_max_retries if max_retries is None else max_retries
    if attempts < 1:
        attempts = 1
    for attempt in range(attempts):
        try:
            return await fn()
        except (RateLimitError, APITimeoutError):
            if attempt == attempts - 1:
                raise
            await asyncio.sleep(min(2**attempt, 16) + random.uniform(0, 1))
    raise RuntimeError("acall_with_retry: hết số lần thử")


async def astream_chat(
    messages: Messages,
    params: GenerationParams | None = None,
    *,
    model: str | None = None,
) -> AsyncIterator[str]:
    """Stream token async (AsyncOpenAI + semaphore + retry). Dùng từ completion.chat_stream."""
    params = params or GenerationParams()
    resolved_model = resolve_model_chain(model)[0]

    async def _open_stream():
        chain = resolve_backend_chain()
        names: list[str | None] = [None] if len(chain) == 1 else [None, *chain[1:]]
        last_exc: Exception | None = None
        for backend_name in names:
            client = (
                get_async_client()
                if backend_name is None
                else get_async_client(backend_name)
            )
            try:
                return await client.chat.completions.create(
                    model=resolved_model,
                    messages=messages,
                    stream=True,
                    **params.to_openai_kwargs(),
                )
            except RateLimitError as exc:
                mark_current_key_limited(client)
                if len(names) == 1:
                    raise
                last_exc = exc
                continue
            except Exception as exc:
                last_exc = exc
                if len(names) == 1:
                    raise
                continue
        if isinstance(last_exc, Exception):
            raise last_exc
        raise RuntimeError("astream_chat: không mở được stream")

    async with async_llm_slot():
        stream = await acall_with_retry(
            _open_stream,
            max_retries=settings.llm_max_retries,
        )
        async for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta


def iter_sync_astream(
    messages: Messages,
    params: GenerationParams | None = None,
    *,
    model: str | None = None,
    stream_completed: list[bool] | None = None,
) -> Iterator[str]:
    """Bridge astream_chat → sync iterator (LangGraph / composer chạy trong thread)."""
    loop = ensure_llm_async_loop()
    out: queue.Queue[Any] = queue.Queue()
    done = object()

    async def _produce() -> None:
        try:
            async for token in astream_chat(messages, params, model=model):
                out.put(token)
        except Exception as exc:
            out.put(exc)
        finally:
            out.put(done)

    task_box: dict[str, asyncio.Task[None]] = {}

    async def _run() -> None:
        task_box["task"] = asyncio.current_task()
        await _produce()

    asyncio.run_coroutine_threadsafe(_run(), loop)
    finished = False
    try:
        while True:
            item = out.get()
            if item is done:
                finished = True
                break
            if isinstance(item, Exception):
                raise item
            yield item
    finally:

        def _cancel() -> None:
            task = task_box.get("task")
            if task is not None and not task.done():
                task.cancel()

        loop.call_soon_threadsafe(_cancel)

    if stream_completed is not None and finished:
        stream_completed.append(True)
