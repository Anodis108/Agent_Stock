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


def evidence_number_tokens(evidence: list[str] | None) -> list[str]:
    """Số liệu có trong evidence (dùng để kiểm grounding sau rewrite)."""
    tokens: list[str] = []
    seen: set[str] = set()
    for e in evidence or []:
        for match in _NUMBER_RE.findall(e):
            token = match.lower().replace(",", ".")
            if token not in seen:
                seen.add(token)
                tokens.append(token)
    return tokens


def has_evidence_grounding(body: str, evidence: list[str] | None = None) -> bool:
    """True nếu câu trả lời còn giữ ít nhất một số liệu từ evidence (khi có số)."""
    nums = evidence_number_tokens(evidence)
    if not nums:
        return True
    blob = (body or "").lower().replace(",", ".")
    return any(_number_supported(n, blob) for n in nums)


def check_rewrite_grounding(
    body: str,
    evidence: list[str] | None = None,
    *,
    require: bool = True,
) -> GuardrailResult:
    """Khi rewrite: không được bỏ hết số liệu evidence đã có."""
    if not require:
        return GuardrailResult(ok=True)
    if has_evidence_grounding(body, evidence):
        return GuardrailResult(ok=True)
    return GuardrailResult(
        ok=False,
        violations=["rewrite làm mất grounding (thiếu số liệu evidence)"],
    )


def strip_buy_sell(text: str) -> str:
    """Gỡ cụm mua/bán chắc chắn, giữ nguyên phần còn lại (số liệu/tin)."""
    out = text or ""
    lower = out.lower()
    for pat in _BUY_SELL_PATTERNS:
        while True:
            idx = lower.find(pat)
            if idx < 0:
                break
            out = out[:idx] + out[idx + len(pat) :]
            lower = out.lower()
    return re.sub(r"\s{2,}", " ", out).strip(" .;")


def rewrite_keep_grounding(
    previous: str,
    evidence: list[str] | None = None,
) -> str:
    """Viết lại an toàn: bỏ mua/bán, giữ số liệu; fallback tóm tắt evidence."""
    evid = list(evidence or [])
    cleaned = strip_buy_sell(previous)
    # Bỏ số không có trong evidence
    if evid:
        evid_blob = " ".join(evid).lower()
        parts: list[str] = []
        last = 0
        for m in _NUMBER_RE.finditer(cleaned):
            token = m.group(0).lower().replace(",", ".")
            parts.append(cleaned[last : m.start()])
            if _number_supported(token, evid_blob):
                parts.append(m.group(0))
            last = m.end()
        parts.append(cleaned[last:])
        cleaned = re.sub(r"\s{2,}", " ", "".join(parts)).strip(" .;")

    disclaimer = "Thông tin tham khảo, không phải lời khuyên đầu tư."
    if cleaned and check_output("", cleaned, evid).ok and has_evidence_grounding(
        cleaned, evid
    ):
        if "không phải lời khuyên" not in cleaned.lower():
            cleaned = f"{cleaned} {disclaimer}"
        return cleaned

    summary = "; ".join(evid) if evid else "không có evidence."
    safe = f"Tóm tắt dữ liệu: {summary} {disclaimer}"
    if check_output("", safe, evid).ok:
        return safe
    return "Không thể trả lời an toàn với evidence hiện có."


def _number_supported(token: str, evidence_blob: str) -> bool:
    if not evidence_blob:
        return False
    variants = {token, token.replace(".", ",")}
    # bỏ dấu % khi so evidence
    bare = token.rstrip("%")
    variants.add(bare)
    variants.add(bare + "%")
    return any(v in evidence_blob for v in variants if v)
