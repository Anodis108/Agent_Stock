"""Eval result cache — tránh gọi LLM lại cho cùng case + prompt hash."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from backend.shared.settings import settings


def _cache_dir() -> Path:
    return Path(settings.eval_cache_dir)


def _case_key(case_id: str, prompt_hash: str) -> str:
    return hashlib.sha256(f"{case_id}:{prompt_hash}".encode()).hexdigest()[:32]


def prompt_hash_from_messages(messages: list[dict[str, str]]) -> str:
    payload = json.dumps(messages, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def get_cached(case_id: str, prompt_hash: str) -> dict[str, Any] | None:
    if not settings.eval_cache_enabled:
        return None
    path = _cache_dir() / f"{_case_key(case_id, prompt_hash)}.json"
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def set_cached(case_id: str, prompt_hash: str, result: dict[str, Any]) -> None:
    if not settings.eval_cache_enabled:
        return
    d = _cache_dir()
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{_case_key(case_id, prompt_hash)}.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
