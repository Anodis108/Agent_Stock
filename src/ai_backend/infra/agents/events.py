"""Hạ tầng dùng chung cho mọi node của Swarm Graph: dependencies theo request, event realtime, cờ huỷ stream,
helper chạy worker theo mã.

deps / cờ huỷ là ContextVar -> mỗi request (mỗi thread/context) có bản riêng, không lẫn dữ liệu giữa các request.
"""

from __future__ import annotations

import contextvars
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from common.logging import get_logger

_logger = get_logger(__name__)

# Dependencies của request hiện tại (price_source, news_source, brains, event_callback...)
graph_deps: contextvars.ContextVar[dict[str, Any]] = contextvars.ContextVar("graph_deps", default={})
_stream_cancel: contextvars.ContextVar[Any | None] = contextvars.ContextVar("_stream_cancel", default=None)


class StreamCancelledError(Exception):
    """Client đóng SSE — dừng pipeline."""


def set_stream_cancel_event(event: Any | None) -> None:
    """Gắn threading.Event từ SSE generator; None để clear."""
    _stream_cancel.set(event)


def check_stream_cancelled() -> None:
    ev = _stream_cancel.get()
    if ev is not None and getattr(ev, "is_set", lambda: False)():
        raise StreamCancelledError("client disconnected")


def emit_agent_event(event: str, data: dict[str, Any]) -> None:
    """Gửi sự kiện thời gian thực (node_start, node_finish, token, chart_url...) đến SSE stream generator."""
    check_stream_cancelled()
    cb = graph_deps.get().get("event_callback")
    if cb:
        try:
            cb(event, data)
            if event == "node_finish":
                cb("node_end", data)
            elif event == "node_end":
                cb("node_finish", data)
        except Exception as exc:
            _logger.warning("Error in event_callback (%s): %s", event, exc)


def target_symbols(state: dict[str, Any]) -> list[str]:
    symbols = list(state.get("symbols") or [])
    if not symbols and state.get("symbol"):
        symbols = [state["symbol"]]
    return symbols


def run_per_symbol(fn, symbols: list[str], *args) -> list[Any]:
    """Chạy fn cho từng mã; nhiều mã thì song song. copy_context để thread con giữ deps/cờ huỷ của request."""
    if len(symbols) <= 1:
        return [fn(s, *args) for s in symbols]
    with ThreadPoolExecutor(max_workers=min(4, len(symbols))) as pool:
        futures = [pool.submit(contextvars.copy_context().run, fn, s, *args) for s in symbols]
        return [f.result() for f in futures]
