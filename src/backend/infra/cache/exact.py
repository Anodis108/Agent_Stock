"""Exact-match LLM response cache — M3-B3 Phase 8.

Cache key = hash(prompt_name, prompt_version, model, normalized_question).
TTL 24h. Store chỉ cần get và setex. Mặc định là memory.
"""

from __future__ import annotations

import hashlib
import os
import re
import time
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Iterator, Protocol

TTL_SECONDS = 24 * 3600

_llm_cache_context: ContextVar[dict[str, Any]] = ContextVar("llm_cache_context", default={})


def normalize_question(text: str) -> str:
    """Chuẩn hóa câu hỏi cho exact-match: trim, lower, gom whitespace."""
    s = (text or "").strip().lower()
    return re.sub(r"\s+", " ", s)


def make_cache_key(
    *,
    prompt_name: str,
    prompt_version: str,
    model: str,
    normalized_question: str,
) -> str:
    payload = f"{prompt_name}|{prompt_version}|{model}|{normalized_question}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class CacheStore(Protocol):
    """Store exact cache. Memory và Redis chỉ cần hai method này."""

    def get(self, key: str) -> str | None: ...

    def setex(self, key: str, ttl_seconds: int, value: str) -> None: ...


class InMemoryStore:
    """Dict trong process. Hết hạn thì get trả None."""

    def __init__(self) -> None:
        self._data: dict[str, tuple[float, str]] = {}

    def get(self, key: str) -> str | None:
        entry = self._data.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if time.time() >= expires_at:
            del self._data[key]
            return None
        return value

    def setex(self, key: str, ttl_seconds: int, value: str) -> None:
        self._data[key] = (time.time() + ttl_seconds, value)

    def clear(self) -> None:
        self._data.clear()

    @property
    def size(self) -> int:
        now = time.time()
        expired = [k for k, (exp, _) in self._data.items() if now >= exp]
        for key in expired:
            del self._data[key]
        return len(self._data)


class ExactCache:
    """Exact cache. get/set đi qua store.setex."""

    def __init__(
        self,
        store: CacheStore | None = None,
        *,
        ttl_seconds: float = TTL_SECONDS,
    ) -> None:
        self._ttl = ttl_seconds
        self._store = store if store is not None else InMemoryStore()

    def make_key(
        self,
        prompt_name: str,
        prompt_version: str,
        model: str,
        normalized_question: str,
    ) -> str:
        return make_cache_key(
            prompt_name=prompt_name,
            prompt_version=prompt_version,
            model=model,
            normalized_question=normalized_question,
        )

    def get(self, key: str) -> str | None:
        return self._store.get(key)

    def set(self, key: str, value: str) -> None:
        self._store.setex(key, int(self._ttl), value)

    def clear(self) -> None:
        clear = getattr(self._store, "clear", None)
        if clear is not None:
            clear()

    @property
    def size(self) -> int:
        size = getattr(self._store, "size", None)
        if isinstance(size, int):
            return size
        return 0


def _default_store() -> CacheStore:
    from backend.shared.settings import settings

    if settings.cache_backend == "redis":
        from backend.infra.cache.redis_store import RedisStore

        return RedisStore()
    return InMemoryStore()


_global_cache: ExactCache | None = None


def get_exact_cache() -> ExactCache:
    global _global_cache
    if _global_cache is None:
        _global_cache = ExactCache(store=_default_store())
    return _global_cache


def reset_exact_cache_for_tests() -> None:
    global _global_cache
    _global_cache = None


def is_exact_cache_enabled() -> bool:
    val = os.environ.get("EXACT_CACHE_ENABLED", "true").lower()
    return val in ("1", "true", "yes")


def set_llm_cache_context(**kwargs: Any) -> None:
    current = dict(_llm_cache_context.get())
    current.update(kwargs)
    _llm_cache_context.set(current)


def clear_llm_cache_context() -> None:
    _llm_cache_context.set({})


def get_llm_cache_context() -> dict[str, Any]:
    return dict(_llm_cache_context.get())


@contextmanager
def llm_cache_scope(
    *,
    prompt_name: str,
    prompt_version: str | int,
    normalized_question: str,
) -> Iterator[None]:
    """Đặt cache context cho một LLM call trong agents."""
    set_llm_cache_context(
        prompt_name=prompt_name,
        prompt_version=str(prompt_version),
        normalized_question=normalized_question,
    )
    try:
        yield
    finally:
        clear_llm_cache_context()
