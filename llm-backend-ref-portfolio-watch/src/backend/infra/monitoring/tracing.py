"""Langfuse tracing — 1 request = 1 trace cha; mỗi bước agent = span con.

Pattern ý tưởng từ `llm-engineer-demo/app/monitoring/tracing.py` (không copy
nguyên file). Tắt mặc định (`MONITORING_ENABLED=false`) — mọi API no-op.
Thiếu key / lỗi init / flush → no-op + cảnh báo, không crash request.
Không dùng ContextVar; span cha tra theo `turn` (uuid mỗi request).
"""

from __future__ import annotations

import hashlib
import re
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
_pending_requests: dict[str, dict[str, Any]] = {}
_guardrail_turns: set[str] = set()
_error_turns: set[str] = set()
_lock = threading.RLock()
_client: Any = None
_warned_missing_keys = False
_warned_init_fail = False

_current_step_box: ContextVar[dict[str, Any] | None] = ContextVar(
    "_current_step_box", default=None
)

KNOWN_AGENT_SPANS = [
    "guardrail", "rewrite", "supervisor", "price", "news", "chart", "composer",
    "pre_rewrite_guardrail", "guardrail_refusal", "rewrite_question",
    "price_agent", "news_agent", "chart_agent", "answer_composer"
]

def redact_pii(text: str) -> str:
    """Mask phone numbers and emails."""
    if not isinstance(text, str):
        return text
    # mask email
    text = re.sub(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', '[EMAIL_REDACTED]', text)
    # mask phone (Vietnam format or generic 10-11 digits)
    text = re.sub(r'(?<!\d)(?:\+84|0)\d{9,10}(?!\d)', '[PHONE_REDACTED]', text)
    return text

def sanitize_trace_payload(data: Any) -> Any:
    """Recursively redact strings in dict/list for trace input/output."""
    if isinstance(data, str):
        return redact_pii(data)
    elif isinstance(data, dict):
        return {k: sanitize_trace_payload(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_trace_payload(item) for item in data]
    return data

def should_sample(
    *,
    is_error: bool = False,
    is_guardrail: bool = False,
    latency_s: float | None = None,
    slow_threshold_s: float = 5.0,
    normal_rate: float = 0.05,
    seed: str | None = None,
) -> bool:
    """Return True always for error, guardrail block, or slow requests."""
    if is_error or is_guardrail:
        return True
    if latency_s is not None and latency_s >= slow_threshold_s:
        return True
    if seed:
        h = int(hashlib.md5(seed.encode()).hexdigest(), 16)
        return (h % 10000) / 10000.0 < normal_rate
    import random

    return random.random() < normal_rate


def mark_turn_guardrail(turn: str) -> None:
    """Đánh dấu turn bị guardrail block — luôn được trace (100% sampling)."""
    if turn:
        with _lock:
            _guardrail_turns.add(turn)


def _wants_trace(turn: str, agent_name: str = "", *, force: bool = False) -> bool:
    if force:
        return True
    with _lock:
        if turn in _guardrail_turns or turn in _error_turns:
            return True
    if agent_name == "guardrail_refusal":
        return True
    return should_sample(seed=turn)


def _ensure_root(turn: str, *, agent_name: str = "", force: bool = False) -> Any | None:
    """Lazy-create Langfuse root trace when first agent span needs it."""
    if not turn or not _enabled():
        return None
    with _lock:
        existing = _roots.get(turn)
        if existing is not None:
            return existing
        pending = _pending_requests.get(turn)
        if pending is None:
            return None
        if not _wants_trace(turn, agent_name, force=force):
            return None

    langfuse = _get_langfuse()
    if langfuse is None:
        return None

    span = None
    try:
        sanitized_input = sanitize_trace_payload(pending["input"])
        meta = dict(pending.get("meta") or {})
        if hasattr(langfuse, "trace"):
            span = langfuse.trace(
                name=pending["name"],
                input=sanitized_input,
                metadata=meta,
            )
        elif hasattr(langfuse, "start_observation"):
            span = langfuse.start_observation(
                name=pending["name"],
                as_type="agent",
                input=sanitized_input,
                metadata=meta,
            )
    except Exception as exc:
        _logger.warning("Không thể khởi tạo trace root: %s", exc)

    if span:
        with _lock:
            _roots[turn] = span
    return span


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
    """Span ROOT — lazy sampling; root tạo khi agent span đầu tiên cần trace."""
    if not _enabled():
        yield {}
        return

    meta = dict(metadata or {})
    turn = str(meta.get("turn") or "")
    if turn:
        with _lock:
            _pending_requests[turn] = {"name": name, "input": input, "meta": meta}

    box: dict[str, Any] = {}
    start = time.perf_counter()
    langfuse = _get_langfuse()
    try:
        yield box
    except Exception as exc:
        if turn:
            with _lock:
                _error_turns.add(turn)
            span = _ensure_root(turn, force=True)
            if span and hasattr(span, "update"):
                span.update(level="ERROR", status_message=str(exc))
        raise
    finally:
        span = step_parent(turn) if turn else None
        latency_s = time.perf_counter() - start
        if span is None and turn and should_sample(latency_s=latency_s, seed=turn):
            span = _ensure_root(turn, force=True)
        if span:
            if hasattr(span, "update"):
                sanitized_output = sanitize_trace_payload(box.get("output"))
                span.update(
                    output=sanitized_output,
                    metadata={"latency_s": latency_s},
                )
            if hasattr(span, "end"):
                span.end()
            if langfuse and hasattr(langfuse, "flush"):
                try:
                    langfuse.flush()
                except Exception as exc:  # noqa: BLE001
                    _logger.warning("Langfuse flush thất bại (best-effort): %s", exc)
        if turn:
            with _lock:
                _roots.pop(turn, None)
                _pending_requests.pop(turn, None)
                _guardrail_turns.discard(turn)
                _error_turns.discard(turn)


@contextmanager
def agent_span(
    turn: str,
    name: str,
    input: Any = None,
    metadata: dict[str, Any] | None = None,
) -> Iterator[dict[str, Any]]:
    """Span AGENT con của root — bọc quanh 1 bước (price/news/eval/…)."""
    if not _enabled():
        yield {}
        return
    root = step_parent(turn)
    if root is None:
        root = _ensure_root(turn, agent_name=name)
    if root is None:
        yield {}
        return

    span = None
    try:
        sanitized_input = sanitize_trace_payload(input)
        if hasattr(root, "span"):
            span = root.span(name=name, input=sanitized_input, metadata=metadata or {})
        elif hasattr(root, "start_observation"):
            span = root.start_observation(
                name=name, as_type="agent", input=sanitized_input, metadata=metadata or {}
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
                sanitized_output = sanitize_trace_payload(box.get("output"))
                span.update(
                    output=sanitized_output,
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
    meta = dict(metadata or {})
    if "prompt_version" not in meta:
        try:
            from backend.infra.cost.tracker import get_cost_context

            meta["prompt_version"] = str(
                get_cost_context().get("prompt_version") or "production"
            )
        except Exception:  # noqa: BLE001
            meta.setdefault("prompt_version", "production")

    try:
        sanitized_input = sanitize_trace_payload(input)
        if effective_model and hasattr(parent_span, "generation"):
            span = parent_span.generation(
                name=name, input=sanitized_input, metadata=meta, model=effective_model
            )
        elif hasattr(parent_span, "span"):
            span = parent_span.span(
                name=name, input=sanitized_input, metadata=meta
            )
        elif hasattr(parent_span, "start_observation"):
            as_type = "generation" if effective_model else "span"
            kwargs: dict[str, Any] = {
                "name": name,
                "as_type": as_type,
                "input": sanitized_input,
                "metadata": meta,
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
                sanitized_output = sanitize_trace_payload(box.get("output"))
                update_kwargs: dict[str, Any] = {
                    "output": sanitized_output,
                    "metadata": {"latency_s": time.perf_counter() - start},
                }
                usage = box.get("usage_details") or box.get("usage")
                if usage:
                    update_kwargs["usage_details"] = usage
                mdl = box.get("model") or effective_model
                if mdl:
                    update_kwargs["model"] = mdl
                    
                # Extract prompt_version if provided in box
                if "prompt_version" in box:
                    update_kwargs["metadata"]["prompt_version"] = box["prompt_version"]
                elif "prompt_version" in meta:
                    update_kwargs["metadata"]["prompt_version"] = meta["prompt_version"]

                try:
                    span.update(**update_kwargs)
                except TypeError:
                    span.update(
                        output=sanitized_output,
                        metadata={"latency_s": time.perf_counter() - start},
                    )
            if hasattr(span, "end"):
                span.end()
