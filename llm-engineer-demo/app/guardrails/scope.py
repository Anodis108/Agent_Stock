"""Topic scope — Buổi 7 / Class 7 slide 28: từ chối câu ngoài phạm vi.

Keyword + mã ticker. Caller truyền bộ từ khóa domain (pháp lý vs cổ phiếu).
"""

from __future__ import annotations

import re

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
