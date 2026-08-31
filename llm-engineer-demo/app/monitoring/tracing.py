"""Monitoring hooks — Buổi 7, Section 4 (LangFuse).

Tối thiểu: 1 trace cho mỗi lần gọi pipeline.answer*(), gắn question/answer/
latency/lỗi. Lời gọi LLM dùng cùng `trace_step(..., model=, usage=)` — type
`generation` + token usage để Langfuse tính cost. KHÔNG bọc qua LangChain.

Mặc định tắt (MONITORING_ENABLED=false) nên khi chưa điền LANGFUSE_* trong
.env, toàn bộ hàm ở đây là no-op — không ai bắt buộc phải cài/kích hoạt
LangFuse để chạy phần còn lại của codebase.
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any

from app.config import settings

# Không ghi span vào graph state — MemorySaver/msgpack không serialize LangfuseSpan.
_parent_span: ContextVar[Any] = ContextVar("langfuse_parent", default=None)


def current_span() -> Any:
    """Span cha của request đang mở (`trace_answer`). None nếu monitoring tắt."""
    return _parent_span.get()


def _get_langfuse():
    """Lazy import + lazy client — tránh phụ thuộc cứng vào package `langfuse`
    khi MONITORING_ENABLED=false, và tránh tạo client ở import-time."""
    from langfuse import Langfuse

    return Langfuse(
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key,
        host=settings.langfuse_host,
    )


@contextmanager
def trace_answer(name: str, question: str, metadata: dict[str, Any] | None = None):
    """Bọc quanh 1 lần gọi pipeline (answer/answer_stream/answer_structured).

    Dùng như:
        with trace_answer("answer", question) as t:
            result = ...
            t["output"] = result

    `t["_span"]` là span cha đang mở — truyền xuống cho trace_step() để tạo
    nested span (xem trace_step()). Chỉ có mặt khi monitoring bật; các call site
    dùng t.get("_span") nên tự an toàn khi tắt.
    """
    if not settings.monitoring_enabled:
        yield {}
        return

    langfuse = _get_langfuse()
    start = time.perf_counter()
    span = langfuse.start_observation(name=name, input=question, metadata=metadata or {})
    box: dict[str, Any] = {"_span": span}
    token = _parent_span.set(span)
    try:
        yield box
    except Exception as exc:
        span.update(level="ERROR", status_message=str(exc))
        raise
    finally:
        _parent_span.reset(token)
        span.update(output=box.get("output"), metadata={"latency_s": time.perf_counter() - start})
        span.end()
        try:
            langfuse.flush()
        except Exception:
            pass


@contextmanager
def trace_step(
    parent_span: Any,
    name: str,
    input: Any = None,
    metadata: dict[str, Any] | None = None,
    *,
    model: str | None = None,
    usage: Any = None,
    model_parameters: dict[str, Any] | None = None,
):
    """Nested child span dưới `parent_span` (lấy từ trace_answer's t["_span"]).

    Dùng trong LangGraph node để thấy từng bước (decompose/retrieve/grade/...)
    lồng nhau trong LangFuse — thay vì 1 span phẳng cho toàn bộ graph.invoke().

    Có `model` hoặc `usage` → observation type `generation` (Langfuse tính cost).
    `parent_span is None` → span của `trace_answer` (ContextVar). Không đưa
    span vào graph state — MemorySaver không serialize được LangfuseSpan.

    Dùng như:
        with trace_step(parent_span, "grade_documents", input=question) as t:
            ...
            t["output"] = graded
        with trace_step(None, "llm.chat", input=messages, model=..., usage=resp.usage) as t:
            t["output"] = text
    """
    if not settings.monitoring_enabled:
        yield {}
        return
    parent = parent_span if parent_span is not None else _parent_span.get()
    if parent is None:
        yield {}
        return

    span = parent.start_observation(
        name=name,
        input=input,
        metadata=metadata or {},
        as_type="generation" if model else "span",
        model=model,
        usage_details=_usage_details(usage),
        model_parameters=model_parameters,
    )

    start = time.perf_counter()
    box: dict[str, Any] = {}
    try:
        yield box
    except Exception as exc:
        span.update(level="ERROR", status_message=str(exc))
        raise
    finally:
        span.update(output=box.get("output"), metadata={"latency_s": time.perf_counter() - start})
        span.end()


def trace_stream(name: str, question: str, tokens: Iterator[str]) -> Iterator[str]:
    """Bọc quanh answer_stream(): trace toàn bộ output ghép lại sau khi stream
    kết thúc (không thể tạo span "giữa chừng" cho streaming)."""
    if not settings.monitoring_enabled:
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
        span = langfuse.start_observation(
            name=name,
            input=question,
            output="".join(chunks),
            metadata={"latency_s": time.perf_counter() - start, "streamed": True},
        )
        span.end()
        langfuse.flush()


def _usage_details(usage: Any) -> dict[str, int] | None:
    """OpenAI usage → Langfuse {input, output, total}."""
    if usage is None:
        return None
    if isinstance(usage, dict):
        prompt, completion, total = (
            usage.get("prompt_tokens"),
            usage.get("completion_tokens"),
            usage.get("total_tokens"),
        )
    else:
        prompt = getattr(usage, "prompt_tokens", None)
        completion = getattr(usage, "completion_tokens", None)
        total = getattr(usage, "total_tokens", None)
    if prompt is None:
        return None
    inp, out = int(prompt), int(completion or 0)
    return {"input": inp, "output": out, "total": int(total if total is not None else inp + out)}


