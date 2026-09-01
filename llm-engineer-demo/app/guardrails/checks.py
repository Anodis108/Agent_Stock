"""Guardrails — Buổi 7 (Evaluation & Guardrails).

check_input(): chạy TRƯỚC khi gọi LLM — injection, toxic, (tuỳ chọn) topic scope.
Raise GuardrailViolation nếu chặn cứng. PII không chặn; caller có thể redact.

check_output(): chạy SAU khi có câu trả lời — độ dài, ngôn ngữ, groundedness số,
toxicity/moderation, PII. KHÔNG raise — trả OutputCheckResult để caller giữ
answer, disclaimer, hoặc fallback.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.config import settings
from app.guardrails.injection import detect_prompt_injection
from app.guardrails.language import looks_vietnamese
from app.guardrails.pii import detect_pii, redact_pii
from app.guardrails.safety import detect_toxicity, moderation_flagged
from app.guardrails.scope import in_topic_scope


class GuardrailViolation(Exception):
    """Input bị chặn bởi guardrails (prompt injection nghi ngờ cao)."""

    def __init__(self, reason: str, details: dict | None = None):
        self.reason = reason
        self.details = details or {}
        super().__init__(reason)


@dataclass(slots=True)
class OutputCheckResult:
    valid: bool
    issues: list[str] = field(default_factory=list)
    answer: str = ""


_FALLBACK_RESPONSE = (
    "Xin lỗi, tôi không thể xác nhận độ chính xác của câu trả lời này. "
    "Vui lòng thử diễn đạt lại câu hỏi hoặc tham khảo trực tiếp văn bản luật."
)

_DISCLAIMER = " (Lưu ý: một số số liệu chưa khớp nguồn đã thu thập trong lượt này.)"


def check_input(
    text: str,
    *,
    topic_keywords: frozenset[str] | None = None,
    extra_scope: str = "",
) -> None:
    """Raise GuardrailViolation nếu injection / toxic / ngoài phạm vi.

    Regex chặn cứng (nhanh, không tốn LLM). LLM-based injection bật qua
    GUARDRAILS_LLM_INJECTION_CHECK. `topic_keywords` None → không check scope
    (pipeline pháp lý giữ hành vi cũ).
    """
    if detect_prompt_injection(text):
        raise GuardrailViolation(
            "prompt_injection_detected",
            {"pattern_match": True},
        )

    if detect_toxicity(text):
        raise GuardrailViolation("unsafe_content", {"pattern_match": True})

    if topic_keywords is not None and not in_topic_scope(
        text, topic_keywords, extra=extra_scope
    ):
        raise GuardrailViolation(
            "out_of_scope",
            {"hint": "Câu hỏi không thuộc phạm vi cổ phiếu niêm yết Việt Nam."},
        )

    if settings.guardrails_llm_injection_check:
        from app.guardrails.injection import llm_injection_check

        result = llm_injection_check(text)
        if result.is_injection and result.confidence >= 0.7:
            raise GuardrailViolation(
                "prompt_injection_detected_llm",
                {"confidence": result.confidence, "reason": result.reason},
            )

    pii_found = detect_pii(text)
    if pii_found:
        # PII không phải injection — không chặn; prepare_input mới redact.
        pass


def prepare_input(
    text: str,
    *,
    redact: bool = False,
    topic_keywords: frozenset[str] | None = None,
    extra_scope: str = "",
) -> str:
    """check_input rồi (tuỳ chọn) che PII trước khi đưa vào LLM."""
    check_input(text, topic_keywords=topic_keywords, extra_scope=extra_scope)
    return redact_pii(text) if redact else text


def check_output(
    answer: str,
    context: list[str],
    *,
    redact: bool = False,
    require_vietnamese: bool = False,
    check_toxicity: bool = True,
    unverified_mode: str = "fallback",
    fallback: str | None = None,
    disclaimer: str | None = None,
) -> OutputCheckResult:
    """Kiểm tra output trước khi trả user. Không raise.

    `unverified_mode`:
      - fallback: số không có trong context → thay cả câu (pipeline pháp lý).
      - disclaimer: giữ câu, gắn cảnh báo (agent cổ phiếu — % có thể làm tròn).
    """
    issues: list[str] = []
    text = answer or ""
    fallback_text = fallback if fallback is not None else _FALLBACK_RESPONSE
    disclaimer_text = disclaimer if disclaimer is not None else _DISCLAIMER

    if len(text) < settings.guardrails_min_answer_len:
        issues.append("answer_too_short")

    if check_toxicity:
        if detect_toxicity(text):
            issues.append("toxic_output")
        if moderation_flagged(text):
            issues.append("moderation_flagged")

    if require_vietnamese and text.strip() and not looks_vietnamese(text):
        issues.append("not_vietnamese")

    if context:
        context_text = " ".join(context)
        numbers_in_answer = re.findall(r"\b\d+\b", text)
        for num in numbers_in_answer:
            if num not in context_text:
                issues.append(f"unverified_number_{num}")

    blocking = {"answer_too_short", "toxic_output", "moderation_flagged", "not_vietnamese"}
    unverified = [i for i in issues if i.startswith("unverified_number_")]
    hard = [i for i in issues if i in blocking]
    if unverified_mode == "fallback":
        hard.extend(unverified)

    if hard:
        return OutputCheckResult(valid=False, issues=issues, answer=fallback_text)

    if unverified:
        text = text.rstrip() + disclaimer_text

    max_len = int(settings.guardrails_max_answer_len or 0)
    if max_len and len(text) > max_len:
        issues.append("answer_too_long")
        text = text[:max_len].rstrip() + "…"

    if redact:
        redacted = redact_pii(text)
        if redacted != text:
            issues.append("pii_redacted")
            text = redacted

    return OutputCheckResult(valid=not issues, issues=issues, answer=text)
