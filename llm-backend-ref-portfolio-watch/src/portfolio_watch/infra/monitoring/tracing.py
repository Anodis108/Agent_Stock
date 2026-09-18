"""Langfuse tracing — 1 request = 1 trace cha; mỗi bước agent = span con.

Pattern ý tưởng từ `llm-engineer-demo/app/monitoring/tracing.py` (không copy
nguyên file). Tắt mặc định (`MONITORING_ENABLED=false`) — mọi API no-op.
Thiếu key / lỗi init / flush → no-op + cảnh báo, không crash request.
Không dùng ContextVar; span cha tra theo `turn` (uuid mỗi request).
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from src.portfolio_watch.shared.logging import get_logger
from src.portfolio_watch.shared.settings import settings

_logger = get_logger(__name__)

_roots: dict[str, Any] = {}
_agents: dict[tuple[str, str], Any] = {}
_client: Any = None
_warned_missing_keys = False
_warned_init_fail = False


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
    _client = None
    _warned_missing_keys = False
    _warned_init_fail = False
    _roots.clear()
    _agents.clear()


def step_parent(turn: str, agent_name: str | None = None) -> Any:
    """Span cha cho trace_step: root (agent_name=None) hoặc agent span."""
    if not turn:
        return None
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
    span = langfuse.start_observation(
        name=name, as_type="agent", input=input, metadata=meta
    )
    if turn:
        _roots[turn] = span
    box: dict[str, Any] = {"_span": span}
    start = time.perf_counter()
    try:
        yield box
    except Exception as exc:
        span.update(level="ERROR", status_message=str(exc))
        raise
    finally:
        span.update(
            output=box.get("output"),
            metadata={"latency_s": time.perf_counter() - start},
        )
        span.end()
        try:
            langfuse.flush()
        except Exception as exc:  # noqa: BLE001
            _logger.warning("Langfuse flush thất bại (best-effort): %s", exc)
        if turn:
            _roots.pop(turn, None)


@contextmanager
def agent_span(
    turn: str,
    name: str,
    input: Any = None,
    metadata: dict[str, Any] | None = None,
) -> Iterator[dict[str, Any]]:
    """Span AGENT con của root — bọc quanh 1 bước (price/news/eval/…)."""
    root = _roots.get(turn)
    if not _enabled() or root is None:
        yield {}
        return

    span = root.start_observation(
        name=name, as_type="agent", input=input, metadata=metadata or {}
    )
    key = (turn, name)
    _agents[key] = span
    box: dict[str, Any] = {}
    start = time.perf_counter()
    try:
        yield box
    except Exception as exc:
        span.update(level="ERROR", status_message=str(exc))
        raise
    finally:
        _agents.pop(key, None)
        span.update(
            output=box.get("output"),
            metadata={"latency_s": time.perf_counter() - start},
        )
        span.end()


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

    as_type = "generation" if model else "span"
    kwargs: dict[str, Any] = {
        "name": name,
        "as_type": as_type,
        "input": input,
        "metadata": metadata or {},
    }
    if model:
        kwargs["model"] = model
    span = parent_span.start_observation(**kwargs)
    box: dict[str, Any] = {}
    start = time.perf_counter()
    try:
        yield box
    except Exception as exc:
        span.update(level="ERROR", status_message=str(exc))
        raise
    finally:
        span.update(
            output=box.get("output"),
            metadata={"latency_s": time.perf_counter() - start},
        )
        span.end()
