"""Guardrail output — rule-based: không lời khuyên mua/bán chắc; số liệu khớp evidence."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_BUY_SELL_PATTERNS = (
    "nên mua",
    "nên bán",
    "nên hold",
    "nên giữ",
    "khuyên mua",
    "khuyên bán",
    "mua ngay",
    "bán ngay",
    "buy now",
    "sell now",
    "strongly buy",
    "strongly sell",
)

_NUMBER_RE = re.compile(
    r"(?<![\w.])[-+]?\d+(?:[.,]\d+)?%?(?![\w])"
)


@dataclass(slots=True)
class GuardrailResult:
    ok: bool
    violations: list[str] = field(default_factory=list)


def find_buy_sell_phrases(text: str) -> list[str]:
    """Trả về các cụm mua/bán chắc chắn tìm thấy (cùng list Guardrail Output)."""
    lowered = (text or "").lower()
    return [pat for pat in _BUY_SELL_PATTERNS if pat in lowered]


def check_output(
    title: str,
    body: str,
    evidence: list[str] | None = None,
) -> GuardrailResult:
    """Kiểm tra nội dung cảnh báo / câu trả lời trước khi gửi user."""
    violations: list[str] = []
    text = f"{title}\n{body}".lower()

    for pat in find_buy_sell_phrases(text):
        violations.append(f"lời khuyên mua/bán chắc chắn: '{pat}'")

    evidence_blob = " ".join(evidence or []).lower()
    for match in _NUMBER_RE.findall(f"{title} {body}"):
        token = match.lower().replace(",", ".")
        # Cho phép số thuần nếu có trong evidence (cùng chuỗi hoặc gần đúng)
        if not _number_supported(token, evidence_blob):
            violations.append(f"số liệu không khớp evidence: '{match}'")

    return GuardrailResult(ok=len(violations) == 0, violations=violations)


def _number_supported(token: str, evidence_blob: str) -> bool:
    if not evidence_blob:
        return False
    variants = {token, token.replace(".", ",")}
    # bỏ dấu % khi so evidence
    bare = token.rstrip("%")
    variants.add(bare)
    variants.add(bare + "%")
    return any(v in evidence_blob for v in variants if v)
