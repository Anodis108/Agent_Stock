"""Provider fallback chain — Module III Bài 7."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any, TypeVar

from backend.shared.settings import settings

T = TypeVar("T")


def resolve_backend_chain() -> list[str]:
    """Primary backend + configured fallbacks (deduped, giữ thứ tự)."""
    chain = [settings.llm_backend.strip().lower()]
    fallbacks = settings.fallback_backends_list
    if not fallbacks:
        # Cascade mặc định theo Phase 5.2 khi primary gặp sự cố kết nối
        if chain[0] == "openai":
            fallbacks = ["ollama", "vllm"]
        elif chain[0] == "ollama":
            fallbacks = ["vllm", "openai"]
        elif chain[0] == "vllm":
            fallbacks = ["ollama", "openai"]
    for name in fallbacks:
        if name not in chain:
            chain.append(name)
    return chain


def resolve_model_chain(model: str | None) -> list[str]:
    """Model ưu tiên + cascade (deduped)."""
    primary = (model or settings.llm_model).strip()
    chain = [primary] if primary else []
    for m in settings.model_cascade_list:
        if m not in chain:
            chain.append(m)
    return chain or [settings.llm_model]


def call_with_model_cascade(
    models: list[str],
    fn: Callable[[str], T],
) -> T:
    """Gọi fn(model) lần lượt theo cascade; raise lỗi cuối nếu tất cả fail."""
    last_exc: Exception | None = None
    for m in models:
        try:
            return fn(m)
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            continue
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("call_with_model_cascade: không có model")


def call_with_backend_fallback(
    fn: Callable[[str | None], T],
) -> T:
    """Gọi fn(backend_name) trên primary rồi fallback backends.

    Khi gọi primary, thử fn(None) trước để tương thích mock get_client() không tham số trong unit tests.
    """
    chain = resolve_backend_chain()
    if len(chain) == 1:
        return fn(None)
    last_exc: Exception | None = None
    for i, backend in enumerate(chain):
        try:
            if i == 0:
                try:
                    return fn(None)
                except TypeError:
                    return fn(backend)
            return fn(backend)
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            continue
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("call_with_backend_fallback: không có backend")
