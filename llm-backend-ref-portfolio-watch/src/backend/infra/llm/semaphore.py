"""LLM concurrency limiter — M3-B4 Phase 10.

Giới hạn số LLM call đồng thời qua biến môi trường ``LLM_SEMAPHORE`` (mặc định 5).
"""

from __future__ import annotations

import os
import threading
from collections.abc import Iterator
from contextlib import contextmanager

_lock = threading.Lock()
_semaphore: threading.Semaphore | None = None
_semaphore_limit: int | None = None


def get_llm_semaphore_limit() -> int:
    raw = os.environ.get("LLM_SEMAPHORE", "5")
    try:
        return max(1, int(raw))
    except ValueError:
        return 5


def get_llm_semaphore() -> threading.Semaphore:
    global _semaphore, _semaphore_limit
    limit = get_llm_semaphore_limit()
    with _lock:
        if _semaphore is None or _semaphore_limit != limit:
            _semaphore = threading.Semaphore(limit)
            _semaphore_limit = limit
        return _semaphore


def reset_llm_semaphore_for_tests() -> None:
    """Reset singleton — chỉ dùng trong pytest."""
    global _semaphore, _semaphore_limit
    with _lock:
        _semaphore = None
        _semaphore_limit = None


@contextmanager
def llm_semaphore_slot() -> Iterator[None]:
    sem = get_llm_semaphore()
    sem.acquire()
    try:
        yield
    finally:
        sem.release()
