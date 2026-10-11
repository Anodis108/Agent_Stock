"""Backward compatibility redirect to backend.infra.llm.client."""

from __future__ import annotations

from backend.infra.llm.client import (
    AiClientError,
    _ai_base,
    _chat_inprocess,
    _default_timeout,
    _is_rate_limited,
    _is_timeout,
    _post_json,
    _post_json_once,
    _retry_delay,
    _scan_inprocess,
    _use_http,
    ai_chat,
    ai_scan,
)

__all__ = [
    "AiClientError",
    "ai_chat",
    "ai_scan",
    "_use_http",
    "_ai_base",
    "_default_timeout",
    "_retry_delay",
    "_is_timeout",
    "_is_rate_limited",
    "_post_json_once",
    "_post_json",
    "_chat_inprocess",
    "_scan_inprocess",
]
