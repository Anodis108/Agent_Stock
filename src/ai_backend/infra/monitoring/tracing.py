"""Monitoring — LangFuse SDK trực tiếp (không LangChain callback).

API:

* ``trace_answer`` — root 1 lượt ``chat`` / ``scan`` / ``scan_resume``.
* ``trace_step(parent, name)`` — bước con dưới ``parent`` tường minh.
  Muốn lồng sâu: ``with trace_step(cha, "a") as box:`` rồi
  ``with trace_step(box["_span"], "b"):`` — hoặc ``_current.set(box["_span"])``
  trước khi gọi subgraph/node khác (LangGraph không cùng một khối ``with``).
* ``current_span()`` — span đang mở (``_current`` hoặc ``context["trace_span"]``).
* ``trace_stream`` — gom token → 1 observation con dưới parent / ``current_span()``.

Khi ``MONITORING_ENABLED=false`` mọi hàm là no-op.
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Literal

from common.settings import settings

# Span đang mở — ``trace_answer`` set root; caller set ``box["_span"]`` khi cần
# bước sau (node LangGraph khác) thụt dưới bước hiện tại.
# LangGraph gọi node ngoài khối ``with``, nên span cha không tự lồng qua lexical
# scope. ``start_as_current_observation`` cũng chỉ là context của SDK — cùng vai
# trò với ô này. Lồng trong một hàm thì truyền ``box["_span"]`` làm parent.
_current: ContextVar[Any] = ContextVar("langfuse_current_span", default=None)

# Icon trên cây Langfuse. Mặc định SDK là ``span`` (ký hiệu ↔).
ObservationType = Literal[
    "span",
    "generation",
    "embedding",
    "agent",
    "tool",
    "chain",
    "retriever",
    "evaluator",
    "guardrail",
]


def _get_langfuse():
    """Lazy import + tạo client LangFuse (tránh import cứng khi monitoring tắt)."""
    from langfuse import Langfuse

    from ai_backend.infra.observability.redaction import redact_deep

    return Langfuse(
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key,
        host=settings.langfuse_host,
        mask=lambda *, data, **_: redact_deep(data),  # che PII trước khi trace rời process
    )


def current_span() -> Any:
    """Span cha đang mở: ``_current`` (ưu tiên) hoặc ``get_runtime().context["trace_span"]``."""
    span = _current.get()
    if span is not None:
        return span
    try:
        from langgraph.runtime import get_runtime

        return (get_runtime().context or {}).get("trace_span")
    except Exception:  # noqa: BLE001 — ngoài graph
        return None


@contextmanager
def trace_answer(
    name: str,
    question: str,
    metadata: dict[str, Any] | None = None,
    as_type: ObservationType = "agent",
):
    """Mở root observation cho **một lượt** pipeline và flush lên LangFuse khi xong.

    Gán root vào ``_current`` để ``current_span()`` / ``trace_step(current_span(), ...)``
    trong graph lấy đúng cha.

    Yields:
        ``box`` — có ``box["_span"]`` khi monitoring bật; gán ``box["output"]`` trước khi thoát.
    """
    if not settings.monitoring_enabled:
        yield {}
        return

    langfuse = _get_langfuse()
    start = time.perf_counter()
    span = langfuse.start_observation(
        name=name, as_type=as_type, input=question, metadata=metadata or {}
    )
    box: dict[str, Any] = {"_span": span}
    token = _current.set(span)
    try:
        yield box
    except Exception as exc:
        span.update(level="ERROR", status_message=str(exc))
        raise
    finally:
        _current.reset(token)
        span.update(output=box.get("output"), metadata={"latency_s": time.perf_counter() - start})
        span.end()
        langfuse.flush()


@contextmanager
def trace_step(
    parent_span: Any,
    name: str,
    input: Any = None,
    metadata: dict[str, Any] | None = None,
    as_type: ObservationType = "span",
):
    """Tạo child observation dưới ``parent_span``. ``None`` → no-op (yield ``{}``).

    Không tự đổi ``_current``. Muốn node/subgraph con thấy bước này là cha::

        with trace_step(current_span(), "price_agent") as box:
            token = _current.set(box["_span"]) if box.get("_span") else None
            try:
                ...
            finally:
                if token is not None:
                    _current.reset(token)

    Cùng một hàm có thể lồng trực tiếp::

        with trace_step(cha, "price_agent") as box:
            with trace_step(box["_span"], "act"):
                ...

    Yields:
        ``box`` với ``box["_span"]`` (khi có parent) để truyền làm cha bước sau.
    """
    if parent_span is None:
        yield {}
        return

    start = time.perf_counter()
    span = parent_span.start_observation(
        name=name, as_type=as_type, input=input, metadata=metadata or {}
    )
    box: dict[str, Any] = {"_span": span}
    try:
        yield box
    except Exception as exc:
        span.update(level="ERROR", status_message=str(exc))
        raise
    finally:
        span.update(output=box.get("output"), metadata={"latency_s": time.perf_counter() - start})
        span.end()


def trace_stream(
    name: str,
    question: str,
    tokens: Iterator[str],
    parent: Any = None,
    as_type: ObservationType = "generation",
) -> Iterator[str]:
    """Gom token → 1 observation con dưới ``parent`` hoặc ``current_span()``; flush ngay khi xong."""
    parent_span = parent if parent is not None else current_span()
    if not settings.monitoring_enabled or parent_span is None:
        yield from tokens
        return

    langfuse = _get_langfuse()
    start = time.perf_counter()
    chunks: list[str] = []
    try:
        for token in tokens:
            chunks.append(token)
            yield token
    finally:
        span = parent_span.start_observation(
            name=name,
            as_type=as_type,
            input=question,
            output="".join(chunks),
            metadata={"latency_s": time.perf_counter() - start, "streamed": True},
        )
        span.end()
        langfuse.flush()
