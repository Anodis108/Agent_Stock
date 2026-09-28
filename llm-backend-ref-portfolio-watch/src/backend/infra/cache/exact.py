"""Exact-match LLM response cache — M3-B3 Phase 8.

Cache key = hash(prompt_name, prompt_version, model, normalized_question).
TTL 24h; MVP in-memory (no Redis).
"""

from __future__ import annotations

import hashlib
import os
import re
import time
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any, Iterator

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


@dataclass(slots=True)
class _CacheEntry:
    value: str
    expires_at: float


class ExactCache:
    """In-memory exact cache với TTL."""

    def __init__(self, *, ttl_seconds: float = TTL_SECONDS) -> None:
        self._ttl = ttl_seconds
        self._store: dict[str, _CacheEntry] = {}

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
        entry = self._store.get(key)
        if entry is None:
            return None
        if time.time() >= entry.expires_at:
            del self._store[key]
            return None
        return entry.value

    def set(self, key: str, value: str) -> None:
        self._store[key] = _CacheEntry(
            value=value,
            expires_at=time.time() + self._ttl,
        )

    def clear(self) -> None:
        self._store.clear()

    @property
    def size(self) -> int:
        self._purge_expired()
        return len(self._store)

    def _purge_expired(self) -> None:
        now = time.time()
        expired = [k for k, v in self._store.items() if now >= v.expires_at]
        for k in expired:
            del self._store[k]


_global_cache = ExactCache()


def get_exact_cache() -> ExactCache:
    return _global_cache


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
