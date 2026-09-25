"""Langfuse tracing — 1 request = 1 trace cha; mỗi bước agent = span con.

Pattern ý tưởng từ `llm-engineer-demo/app/monitoring/tracing.py` (không copy
nguyên file). Tắt mặc định (`MONITORING_ENABLED=false`) — mọi API no-op.
Thiếu key / lỗi init / flush → no-op + cảnh báo, không crash request.
Không dùng ContextVar; span cha tra theo `turn` (uuid mỗi request).
"""

from __future__ import annotations

import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any

from backend.shared.logging import get_logger
from backend.shared.settings import settings

_logger = get_logger(__name__)

_roots: dict[str, Any] = {}
_agents: dict[tuple[str, str], Any] = {}
_lock = threading.RLock()
_client: Any = None
_warned_missing_keys = False
_warned_init_fail = False

_current_step_box: ContextVar[dict[str, Any] | None] = ContextVar(
    "_current_step_box", default=None
)


def record_step_usage(
    *,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    total_tokens: int = 0,
    model: str | None = None,
) -> None:
    """Ghi nhận token usage và model vào step hiện tại (cho Langfuse generation & cost)."""
    box = _current_step_box.get()
    if box is not None:
        usage = box.setdefault("usage_details", {"input": 0, "output": 0, "total": 0})
        usage["input"] += prompt_tokens
        usage["output"] += completion_tokens
        usage["total"] += total_tokens
        if model:
            box["model"] = model


def _enabled() -> bool:
    """True chỉ khi bật monitoring *và* có đủ public/secret key."""
    global _warned_missing_keys
    if not settings.monitoring_enabled:
        return False
    if not (settings.langfuse_public_key and settings.langfuse_secret_key):
        if not _warned_missing_keys:
            _logger.warning(
                "MONITORING_ENABLED=true nhưng thiếu LANGFUSE_PUBLIC_KEY / "
                "LANGFUSE_SECRET_KEY — tracing no-op"
            )
            _warned_missing_keys = True
        return False
    return True


def _get_langfuse() -> Any | None:
    """Lazy import Langfuse — thiếu package / lỗi init → None (no-op)."""
    global _client, _warned_init_fail
    if not _enabled():
        return None
    if _client is False:
        return None
    if _client is not None:
        return _client
    try:
        import os

        from langfuse import Langfuse

        cert = os.environ.get("SSL_CERT_FILE")
        if cert and not os.path.isfile(cert):
            os.environ.pop("SSL_CERT_FILE", None)

        _client = Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
        )
        return _client
    except Exception as exc:  # noqa: BLE001 — monitoring best-effort
        if not _warned_init_fail:
            _logger.warning("Langfuse init thất bại — tracing no-op: %s", exc)
            _warned_init_fail = True
        _client = False
        return None


def reset_client_for_tests() -> None:
    """Chỉ dùng trong pytest — xoá client cache + cờ cảnh báo."""
    global _client, _warned_missing_keys, _warned_init_fail
    with _lock:
        _client = None
        _warned_missing_keys = False
        _warned_init_fail = False
        _roots.clear()
        _agents.clear()


def step_parent(turn: str, agent_name: str | None = None) -> Any:
    """Span cha cho trace_step: root (agent_name=None) hoặc agent span."""
    if not turn:
        return None
    with _lock:
        if agent_name:
            return _agents.get((turn, agent_name))
        return _roots.get(turn)


@contextmanager
def trace_request(
    name: str,
    input: Any,
    metadata: dict[str, Any] | None = None,
) -> Iterator[dict[str, Any]]:
    """Span ROOT — 1 lần / chat hoặc scan. `box["_span"]` / `box["output"]`."""
    if not _enabled():
        yield {}
        return

    langfuse = _get_langfuse()
    if langfuse is None:
        yield {}
        return

    meta = dict(metadata or {})
    turn = str(meta.get("turn") or "")
    span = None
    try:
        if hasattr(langfuse, "trace"):
            span = langfuse.trace(name=name, input=input, metadata=meta)
        elif hasattr(langfuse, "start_observation"):
            span = langfuse.start_observation(
                name=name, as_type="agent", input=input, metadata=meta
            )
    except Exception as exc:
        _logger.warning("Không thể khởi tạo trace root: %s", exc)

    if turn and span:
        with _lock:
            _roots[turn] = span
    box: dict[str, Any] = {"_span": span}
    start = time.perf_counter()
    try:
        yield box
    except Exception as exc:
        if span and hasattr(span, "update"):
            span.update(level="ERROR", status_message=str(exc))
        raise
    finally:
        if span:
            if hasattr(span, "update"):
                span.update(
                    output=box.get("output"),
                    metadata={"latency_s": time.perf_counter() - start},
                )
            if hasattr(span, "end"):
                span.end()
            try:
                if hasattr(langfuse, "flush"):
                    langfuse.flush()
            except Exception as exc:  # noqa: BLE001
                _logger.warning("Langfuse flush thất bại (best-effort): %s", exc)
        if turn:
            with _lock:
                _roots.pop(turn, None)


@contextmanager
def agent_span(
    turn: str,
    name: str,
    input: Any = None,
    metadata: dict[str, Any] | None = None,
) -> Iterator[dict[str, Any]]:
    """Span AGENT con của root — bọc quanh 1 bước (price/news/eval/…)."""
    root = step_parent(turn)
    if not _enabled() or root is None:
        yield {}
        return

    span = None
    try:
        if hasattr(root, "span"):
            span = root.span(name=name, input=input, metadata=metadata or {})
        elif hasattr(root, "start_observation"):
            span = root.start_observation(
                name=name, as_type="agent", input=input, metadata=metadata or {}
            )
    except Exception as exc:
        _logger.warning("Không thể khởi tạo agent span: %s", exc)

    key = (turn, name)
    if span:
        with _lock:
            _agents[key] = span
    box: dict[str, Any] = {}
    start = time.perf_counter()
    try:
        yield box
    except Exception as exc:
        if span and hasattr(span, "update"):
            span.update(level="ERROR", status_message=str(exc))
        raise
    finally:
        with _lock:
            _agents.pop(key, None)
        if span:
            if hasattr(span, "update"):
                span.update(
                    output=box.get("output"),
                    metadata={"latency_s": time.perf_counter() - start},
                )
            if hasattr(span, "end"):
                span.end()


@contextmanager
def agent_step(
    turn: str,
    agent_name: str,
    step_name: str,
    input: Any = None,
    metadata: dict[str, Any] | None = None,
    *,
    model: str | None = None,
) -> Iterator[dict[str, Any]]:
    """Step span dưới agent — bọc trace_step(step_parent(turn, agent_name), …)."""
    parent = step_parent(turn, agent_name)
    with trace_step(
        parent, step_name, input=input, metadata=metadata, model=model
    ) as box:
        yield box


@contextmanager
def trace_step(
    parent_span: Any,
    name: str,
    input: Any = None,
    metadata: dict[str, Any] | None = None,
    *,
    model: str | None = None,
) -> Iterator[dict[str, Any]]:
    """Span/generation con của parent — no-op nếu parent None."""
    if not _enabled() or parent_span is None:
        yield {}
        return

    # Tự động nhận diện các step gọi LLM nếu chưa có model
    llm_step_names = {
        "rewrite",
        "route",
        "routing",
        "draft",
        "classify",
        "eval_severity",
        "evaluate",
        "draft_attempt",
        "react_step",
    }
    effective_model = model or (settings.llm_model if name in llm_step_names else None)

    span = None
    try:
        if effective_model and hasattr(parent_span, "generation"):
            span = parent_span.generation(
                name=name, input=input, metadata=metadata or {}, model=effective_model
            )
        elif hasattr(parent_span, "span"):
            span = parent_span.span(
                name=name, input=input, metadata=metadata or {}
            )
        elif hasattr(parent_span, "start_observation"):
            as_type = "generation" if effective_model else "span"
            kwargs: dict[str, Any] = {
                "name": name,
                "as_type": as_type,
                "input": input,
                "metadata": metadata or {},
            }
            if effective_model:
                kwargs["model"] = effective_model
            span = parent_span.start_observation(**kwargs)
    except Exception as exc:
        _logger.warning("Không thể khởi tạo trace step: %s", exc)

    box: dict[str, Any] = {}
    if effective_model:
        box["model"] = effective_model

    token = _current_step_box.set(box)
    start = time.perf_counter()
    try:
        yield box
    except Exception as exc:
        if span and hasattr(span, "update"):
            span.update(level="ERROR", status_message=str(exc))
        raise
    finally:
        _current_step_box.reset(token)
        if span:
            if hasattr(span, "update"):
                update_kwargs: dict[str, Any] = {
                    "output": box.get("output"),
                    "metadata": {"latency_s": time.perf_counter() - start},
                }
                usage = box.get("usage_details") or box.get("usage")
                if usage:
                    update_kwargs["usage_details"] = usage
                mdl = box.get("model") or effective_model
                if mdl:
                    update_kwargs["model"] = mdl
                try:
                    span.update(**update_kwargs)
                except TypeError:
                    span.update(
                        output=box.get("output"),
                        metadata={"latency_s": time.perf_counter() - start},
                    )
            if hasattr(span, "end"):
                span.end()
