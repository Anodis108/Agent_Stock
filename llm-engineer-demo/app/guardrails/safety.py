"""Content safety — Class 7 slide 27: lọc toxic / harmful trước khi trả user.

Regex nhanh (luôn). OpenAI Moderation API tùy chọn (GUARDRAILS_MODERATION) —
fail-open nếu không có key / backend local.
"""

from __future__ import annotations

import re

from app.config import settings

_TOXIC = [
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\bkill yourself\b",
        r"\b(suicide bomb|make a bomb)\b",
        r"\b(địt|đụ|lồn|cặc)\b",
        r"\b(nổ tung|chế bom)\b",
    )
]


def detect_toxicity(text: str) -> bool:
    """Regex — bắt nội dung độc hại rõ. Không chặn từ chứng khoán (giảm sàn, cắt lỗ)."""
    blob = text or ""
    return any(p.search(blob) for p in _TOXIC)


def moderation_flagged(text: str) -> bool:
    """OpenAI omni-moderation. Tắt mặc định; lỗi mạng → False (không chặn nhầm)."""
    if not settings.guardrails_moderation or not (text or "").strip():
        return False
    if (not settings.api_keys) or settings.llm_backend != "openai":
        return False
    try:
        from app.llm.client import get_client

        resp = get_client().moderations.create(model="omni-moderation-latest", input=text)
        return bool(resp.results and resp.results[0].flagged)
    except Exception:
        return False
