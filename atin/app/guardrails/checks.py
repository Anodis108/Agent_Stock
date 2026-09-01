"""Guardrails tối giản: injection/toxic chặn input, PII redact, kiểm tra output.

Ba lớp cơ bản đủ cho Phase 1 — không kéo theo LLM-based check / moderation API
của bản đầy đủ (llm-engineer-demo), giữ atin/ nhẹ và độc lập.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.config import settings

_INJECTION_PATTERNS = [
    re.compile(r"ignore (all |previous |above )?instructions", re.IGNORECASE),
    re.compile(r"disregard (all |previous |above )?(instructions|rules)", re.IGNORECASE),
    re.compile(r"bỏ qua (mọi |các )?(hướng dẫn|chỉ dẫn|quy tắc)", re.IGNORECASE),
    re.compile(r"reveal (your |the )?system prompt", re.IGNORECASE),
    re.compile(r"tiết lộ.*system prompt", re.IGNORECASE),
    re.compile(r"you are now", re.IGNORECASE),
    re.compile(r"act as (if you|a) ", re.IGNORECASE),
]

_TOXIC_WORDS = frozenset({"đụ", "địt", "đéo", "fuck", "shit", "cút", "óc chó"})

_PHONE = re.compile(r"\b0\d{9,10}\b")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")


class GuardrailViolation(Exception):
    def __init__(self, reason: str, details: dict | None = None):
        self.reason = reason
        self.details = details or {}
        super().__init__(reason)


@dataclass(slots=True)
class OutputCheckResult:
    valid: bool
    issues: list[str] = field(default_factory=list)
    answer: str = ""


def detect_prompt_injection(text: str) -> bool:
    return any(p.search(text or "") for p in _INJECTION_PATTERNS)


def detect_toxicity(text: str) -> bool:
    low = (text or "").lower()
    return any(w in low for w in _TOXIC_WORDS)


def redact_pii(text: str) -> str:
    text = _PHONE.sub("[SĐT ẩn]", text or "")
    text = _EMAIL.sub("[email ẩn]", text)
    return text


def check_input(text: str) -> None:
    """Raise GuardrailViolation nếu injection / toxic. PII không chặn — caller tự redact."""
    if detect_prompt_injection(text):
        raise GuardrailViolation("prompt_injection_detected", {"pattern_match": True})
    if detect_toxicity(text):
        raise GuardrailViolation("unsafe_content", {"pattern_match": True})


_FALLBACK = "Xin lỗi, tôi chưa đủ dữ liệu đáng tin để trả lời. Hãy hỏi lại rõ hơn."
_DISCLAIMER = " (Lưu ý: số liệu dựa trên dữ liệu mẫu demo.)"


def check_output(answer: str, evidence: list[str]) -> OutputCheckResult:
    """Không raise — trả kết quả để caller quyết định giữ answer, thêm disclaimer, hay fallback."""
    issues: list[str] = []
    text = answer or ""

    if len(text) < settings.guardrails_min_answer_len:
        issues.append("answer_too_short")
    if detect_toxicity(text):
        issues.append("toxic_output")

    context_text = " ".join(evidence)
    numbers = re.findall(r"\b\d+\b", text)
    unverified = [n for n in numbers if n not in context_text]

    if "answer_too_short" in issues or "toxic_output" in issues:
        return OutputCheckResult(valid=False, issues=issues, answer=_FALLBACK)

    if unverified:
        issues.append("unverified_numbers")
        text = text.rstrip() + _DISCLAIMER

    redacted = redact_pii(text)
    if redacted != text:
        issues.append("pii_redacted")
        text = redacted

    max_len = settings.guardrails_max_answer_len
    if max_len and len(text) > max_len:
        issues.append("answer_too_long")
        text = text[:max_len].rstrip() + "…"

    return OutputCheckResult(valid=not issues, issues=issues, answer=text)
