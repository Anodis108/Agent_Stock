"""Async LLM client. chat_stream gọi module này.

AsyncOpenAI không chặn event loop của FastAPI. Retry dùng asyncio.sleep.
Semaphore asyncio lấy giới hạn từ llm.max_concurrency trong config.yaml.
Mọi lời gọi dùng chung một event loop để semaphore giới hạn được các stream chạy song song.
"""

from __future__ import annotations

import asyncio
import random
import threading
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from openai import APITimeoutError, AsyncOpenAI, RateLimitError

from ai_backend.infra.llm.backends import get_backend
from ai_backend.infra.llm.client import _get_pool
from common.settings import settings

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
