"""Domain Guardrails package for AI Backend Microservice.

Bao gồm:
- InputGuardrail: Chặn 100% Prompt Injection, lọc câu hỏi Out-of-Scope.
- GreetingFastpath: Nhận diện câu chào hỏi để phản hồi tức thì (TTFT < 1s).
- OutputGuardrail: Bắt buộc Disclaimer, định dạng bảng P&L, đối chiếu grounding số liệu.
"""

from ai_backend.domain.guardrails.greeting_fastpath import (
    DEFAULT_GREETING_RESPONSE,
    FastpathGreetingResult,
    GreetingFastpath,
    is_greeting,
    is_pure_greeting,
)
from ai_backend.domain.guardrails.input_guardrail import (
    INVESTMENT_DISCLAIMER,
    GuardrailCategory,
    InputGuardrail,
    InputGuardrailResult,
    check_input_guardrail,
)
from ai_backend.domain.guardrails.output_checks import (
    DEFAULT_DISCLAIMER,
    GuardrailResult,
    OutputGuardrail,
    check_output,
    check_rewrite_grounding,
    find_buy_sell_phrases,
    format_pnl_table,
    has_evidence_grounding,
    mask_structural_numbers,
    rewrite_keep_grounding,
    strip_buy_sell,
)

__all__ = [
    "InputGuardrail",
    "check_input_guardrail",
    "InputGuardrailResult",
    "GuardrailCategory",
    "INVESTMENT_DISCLAIMER",
    "GreetingFastpath",
    "is_greeting",
    "is_pure_greeting",
    "FastpathGreetingResult",
    "DEFAULT_GREETING_RESPONSE",
    "OutputGuardrail",
    "check_output",
    "check_rewrite_grounding",
    "find_buy_sell_phrases",
    "format_pnl_table",
    "has_evidence_grounding",
    "mask_structural_numbers",
    "rewrite_keep_grounding",
    "strip_buy_sell",
    "GuardrailResult",
    "DEFAULT_DISCLAIMER",
]
