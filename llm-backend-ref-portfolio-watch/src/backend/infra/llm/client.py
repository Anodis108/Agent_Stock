"""OpenAI client factory — hỗ trợ openai / ollama / vllm."""

from __future__ import annotations

from openai import OpenAI

from backend.infra.llm.backends import get_backend
from backend.infra.llm.resilience import RotatingKeyPool
from backend.shared.settings import settings

_pool: RotatingKeyPool | None = None


def _get_pool() -> RotatingKeyPool:
    global _pool
    if _pool is None:
        _pool = RotatingKeyPool(settings.api_keys)
    return _pool


def _resolve_base_url(default_base_url: str) -> str | None:
    if settings.llm_base_url:
        return settings.llm_base_url
    return default_base_url or None


def get_client() -> OpenAI:
    backend = get_backend(settings.llm_backend)
    base_url = _resolve_base_url(backend.default_base_url)
    api_key = _get_pool().get_key() if backend.requires_real_key else backend.dummy_key
    return OpenAI(api_key=api_key, base_url=base_url)


def mark_current_key_limited(client: OpenAI, cooldown_seconds: float = 60.0) -> None:
    backend = get_backend(settings.llm_backend)
    if backend.requires_real_key and client.api_key:
        _get_pool().mark_limited(client.api_key, cooldown_seconds)
