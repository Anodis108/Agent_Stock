"""Log gọn sau mỗi bước agent (patch từ LangGraph stream updates)."""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel

from ai_backend.shared.logging import get_logger

_logger = get_logger("ai_backend.domain.agents.scan.step")


def log_agent_step(step: str, patch: dict[str, Any]) -> None:
    def safe(value: Any) -> Any:
        if isinstance(value, BaseModel):
            return value.model_dump()
        if isinstance(value, list):
            if value and hasattr(value[0], "type"):
                rows: list[dict[str, Any]] = []
                for m in value:
                    kind = getattr(m, "type", None) or getattr(m, "role", "?")
                    row: dict[str, Any] = {"kind": kind}
                    content = getattr(m, "content", None) or ""
                    if content:
                        row["content"] = content if len(content) <= 200 else content[:200] + "…"
                    name = getattr(m, "name", None)
                    if name:
                        row["name"] = name
                    tool_calls = getattr(m, "tool_calls", None)
                    if tool_calls:
                        row["tool_calls"] = [
                            tc.get("name") if isinstance(tc, dict) else getattr(tc, "name", None)
                            for tc in tool_calls
                        ]
                    rows.append(row)
                return rows
            return [safe(v) for v in value]
        if isinstance(value, dict):
            return {k: safe(v) for k, v in value.items()}
        return value

    payload = {"step": step, "patch": safe(patch or {})}
    _logger.info("\n%s", json.dumps(payload, ensure_ascii=False, indent=2))
