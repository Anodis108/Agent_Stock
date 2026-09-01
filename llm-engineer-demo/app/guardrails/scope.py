"""Topic scope — Buổi 7 / Class 7 slide 28: từ chối câu ngoài phạm vi.

Hai lớp (Class 7 "Guardrails Architecture: Full Stack" — cùng tinh thần 3 lớp
phòng thủ injection ở guardrails/injection.py):
  1. Keyword + regex ticker — nhanh, rẻ, chạy mọi request.
  2. LLM-based check (llm_scope_check) — chỉ chạy khi lớp 1 không chắc (không
     match ticker/keyword), bắt câu lạc đề viết khéo (không chứa từ khóa
     nhưng rõ ràng không phải hỏi cổ phiếu) mà regex bỏ sót. Tắt mặc định qua
     GUARDRAILS_LLM_SCOPE_CHECK — cùng cấu hình pattern với injection check.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, Field

_TICKER = re.compile(r"\b[A-Z]{3,4}\b")


def in_topic_scope(
    text: str,
    keywords: frozenset[str],
    *,
    extra: str = "",
) -> bool:
    """True nếu `text` (cộng `extra`, vd. mã gợi ý) thuộc domain `keywords` hoặc có ticker."""
    blob = f"{extra} {text}".strip()
    if not blob:
        return False
    if _TICKER.search(blob.upper()):
        return True
    low = blob.lower()
    return any(k in low for k in keywords)


class _ScopeCheck(BaseModel):
    in_scope: bool = Field(description="Câu hỏi có thuộc phạm vi domain đã mô tả không")
    reason: str = Field(description="Giải thích ngắn gọn")


def llm_scope_check(text: str, domain_desc: str) -> _ScopeCheck:
    """Check bằng LLM — bắt câu lạc đề không chứa keyword/ticker (viết khéo,
    diễn đạt gián tiếp) mà lớp regex/keyword bỏ sót. Tốn 1 lời gọi LLM."""
    from app.llm import completion
    from app.llm.params import GenerationParams

    messages = [
        {
            "role": "system",
            "content": (
                f"Phạm vi hợp lệ: {domain_desc}. "
                "Phân loại xem câu hỏi của user có thuộc phạm vi này không — "
                "kể cả khi không chứa từ khóa rõ ràng, miễn ý hỏi liên quan domain."
            ),
        },
        {"role": "user", "content": text},
    ]
    return completion.chat_parsed(messages, _ScopeCheck, GenerationParams(temperature=0.0))
