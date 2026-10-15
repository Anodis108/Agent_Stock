"""Output Guardrail — Kiểm tra và định dạng đầu ra câu trả lời của AI.

Nhiệm vụ:
1. Bắt buộc Tuyên bố miễn trừ trách nhiệm (Investment Disclaimer).
2. Phát hiện và loại bỏ các lời khuyên mua/bán cổ phiếu chắc chắn (find_buy_sell_phrases, strip_buy_sell).
3. Đảm bảo Grounding: Số liệu tài chính nêu ra phải khớp với facts thu thập trong evidence (check_output, mask_structural_numbers).
4. Định dạng bảng P&L danh mục đầu tư chuẩn Markdown (format_pnl_table).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# Các cụm từ khuyến nghị mua/bán chắc chắn bị cấm
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

# Regex trích xuất số và tỷ lệ phần trăm
_NUMBER_RE = re.compile(
    r"(?<![\w.])[-+]?\d+(?:[.,]\d+)?%?(?![\w])"
)

DEFAULT_DISCLAIMER = "Thông tin tham khảo, không phải lời khuyên đầu tư."


@dataclass(slots=True)
class GuardrailResult:
    """Kết quả kiểm tra đầu ra từ Guardrail."""
    ok: bool
    violations: list[str] = field(default_factory=list)


def find_buy_sell_phrases(text: str) -> list[str]:
    """Trả về các cụm từ mua/bán chắc chắn tìm thấy trong văn bản."""
    lowered = (text or "").lower()
    return [pat for pat in _BUY_SELL_PATTERNS if pat in lowered]


def mask_structural_numbers(text: str) -> str:
    """Loại bỏ số thứ tự danh sách, bước, mục, quý, tháng trước khi kiểm tra grounding số liệu.

    Ví dụ: '1. Tiêu đề', '4. Nghị quyết', 'Bước 2:', 'Quý 3' là định dạng trình bày,
    không phải số liệu tài chính cần đối chiếu evidence.
    """
    if not text:
        return ""
    # 1. Số thứ tự đầu dòng: "1. ", "2. ", "1) ", "(1) "
    out = re.sub(r"(?m)^\s*\(?\d+\)?[.)]\s+", " ", text)
    # 2. Cụm chỉ mục, bước, quý, tháng, top: "mục 1", "bước 2", "quý 3", "top 5"
    out = re.sub(
        r"\b(?:mục|bước|phần|top|quý|tháng|phiên thứ|thứ)\s+\d+\b",
        " ",
        out,
        flags=re.IGNORECASE,
    )
    return out


def _number_supported(token: str, evidence_blob: str) -> bool:
    """Kiểm tra token số có xuất hiện trong evidence blob hay không."""
    if not evidence_blob:
        return False
    variants = {token, token.replace(".", ",")}
    bare = token.rstrip("%")
    variants.add(bare)
    variants.add(bare + "%")
    return any(v in evidence_blob for v in variants if v)


def check_output(
    title: str,
    body: str,
    evidence: list[str] | None = None,
) -> GuardrailResult:
    """Kiểm tra tính hợp lệ của câu trả lời trước khi gửi ra ngoài."""
    violations: list[str] = []
    text = f"{title}\n{body}".lower()

    # 1. Kiểm tra cụm mua/bán chắc chắn
    for pat in find_buy_sell_phrases(text):
        violations.append(f"lời khuyên mua/bán chắc chắn: '{pat}'")

    # 2. Kiểm tra số liệu có được bảo đảm bởi evidence không
    evidence_blob = " ".join(evidence or []).lower()
    content_for_nums = mask_structural_numbers(f"{title}\n{body}")
    for match in _NUMBER_RE.findall(content_for_nums):
        token = match.lower().replace(",", ".")
        if not _number_supported(token, evidence_blob):
            violations.append(f"số liệu không khớp evidence: '{match}'")

    return GuardrailResult(ok=len(violations) == 0, violations=violations)


def evidence_number_tokens(evidence: list[str] | None) -> list[str]:
    """Trích xuất danh sách token số có trong evidence."""
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
    """Kiểm tra câu trả lời còn giữ ít nhất một số liệu từ evidence (khi có số)."""
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
    """Khi viết lại: không được làm mất toàn bộ số liệu evidence."""
    if not require:
        return GuardrailResult(ok=True)
    if has_evidence_grounding(body, evidence):
        return GuardrailResult(ok=True)
    return GuardrailResult(
        ok=False,
        violations=["rewrite làm mất grounding (thiếu số liệu evidence)"],
    )


def strip_buy_sell(text: str) -> str:
    """Loại bỏ các cụm từ mua/bán chắc chắn khỏi câu trả lời."""
    out = text or ""
    lower = out.lower()
    for pat in _BUY_SELL_PATTERNS:
        while True:
            idx = lower.find(pat)
            if idx < 0:
                break
            out = out[:idx] + out[idx + len(pat) :]
            lower = out.lower()
    return re.sub(r"[ \t]{2,}", " ", out).strip(" .;")


def rewrite_keep_grounding(
    previous: str,
    evidence: list[str] | None = None,
) -> str:
    """Viết lại câu trả lời đảm bảo an toàn: gỡ mua/bán, giữ số liệu facts, kèm disclaimer."""
    evid = list(evidence or [])
    cleaned = strip_buy_sell(previous)

    # Loại bỏ số liệu không có trong evidence (trừ số thứ tự danh sách)
    if evid:
        evid_blob = " ".join(evid).lower()
        parts: list[str] = []
        last = 0
        for m in _NUMBER_RE.finditer(cleaned):
            start, end = m.start(), m.end()
            prefix = cleaned[:start]
            last_nl = prefix.rfind("\n")
            line_prefix = prefix[last_nl + 1 :] if last_nl >= 0 else prefix
            is_list_marker = (
                line_prefix.strip() == ""
                and end < len(cleaned)
                and cleaned[end : end + 2] in (". ", ") ")
            )

            token = m.group(0).lower().replace(",", ".")
            parts.append(cleaned[last : start])
            if is_list_marker or _number_supported(token, evid_blob):
                parts.append(m.group(0))
            last = end
        parts.append(cleaned[last:])
        cleaned = re.sub(r"[ \t]{2,}", " ", "".join(parts))
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip(" .;")

    disclaimer = DEFAULT_DISCLAIMER
    if cleaned and check_output("", cleaned, evid).ok and has_evidence_grounding(cleaned, evid):
        if "không phải lời khuyên" not in cleaned.lower():
            cleaned = f"{cleaned.rstrip()}\n\n{disclaimer}"
        return cleaned

    summary = "; ".join(evid) if evid else "không có evidence."
    safe = f"Tóm tắt dữ liệu: {summary}\n\n{disclaimer}"
    if check_output("", safe, evid).ok:
        return safe
    return "Không thể trả lời an toàn với evidence hiện có."


def format_pnl_table(
    holdings: list[dict[str, Any]],
    nav: float | None = None,
) -> str:
    """Định dạng bảng P&L danh mục đầu tư chuẩn Markdown.

    Cột hiển thị:
    | Mã CP | Khối lượng | Giá vốn (VND) | Thị giá (VND) | Lãi/Lỗ (VND) | Tỷ suất (%) |
    """
    if not holdings:
        return "_Danh mục hiện chưa có cổ phiếu nào._"

    lines = [
        "| Mã CP | Khối lượng | Giá vốn (VND) | Thị giá (VND) | Lãi/Lỗ (VND) | Tỷ suất (%) |",
        "| :---: | :---: | :---: | :---: | :---: | :---: |",
    ]

    total_cost = 0.0
    total_market_value = 0.0
    total_pnl = 0.0

    for h in holdings:
        sym = str(h.get("symbol") or h.get("ticker") or "").upper()
        qty = float(h.get("quantity") or h.get("shares") or 0.0)
        cost = float(h.get("cost_basis") or h.get("avg_price") or h.get("cost") or 0.0)
        market = float(h.get("market_price") or h.get("latest_price") or h.get("price") or cost)
        
        cost_val = qty * cost
        market_val = qty * market
        pnl = market_val - cost_val
        pnl_pct = (pnl / cost_val * 100.0) if cost_val > 0 else 0.0

        total_cost += cost_val
        total_market_value += market_val
        total_pnl += pnl

        pnl_sign = "+" if pnl > 0 else ""
        pnl_pct_sign = "+" if pnl_pct > 0 else ""

        lines.append(
            f"| **{sym}** | {qty:,.0f} | {cost:,.0f} | {market:,.0f} | "
            f"{pnl_sign}{pnl:,.0f} | {pnl_pct_sign}{pnl_pct:.2f}% |"
        )

    # Dòng tổng kết
    total_pnl_sign = "+" if total_pnl > 0 else ""
    total_pnl_pct = (total_pnl / total_cost * 100.0) if total_cost > 0 else 0.0
    total_pct_sign = "+" if total_pnl_pct > 0 else ""

    lines.append(
        f"| **TỔNG** | — | **{total_cost:,.0f}** | **{total_market_value:,.0f}** | "
        f"**{total_pnl_sign}{total_pnl:,.0f}** | **{total_pct_sign}{total_pnl_pct:.2f}%** |"
    )

    if nav is not None and nav > 0:
        lines.append(f"\n**Tổng tài sản danh mục (NAV):** `{nav:,.0f} VND`")

    lines.append(f"\n_{DEFAULT_DISCLAIMER}_")
    return "\n".join(lines)


class OutputGuardrail:
    """Class wrapper cho Output Guardrail Engine."""

    @classmethod
    def check(cls, title: str, body: str, evidence: list[str] | None = None) -> GuardrailResult:
        return check_output(title, body, evidence)

    @classmethod
    def strip_buy_sell_phrases(cls, text: str) -> str:
        return strip_buy_sell(text)

    @classmethod
    def rewrite_safely(cls, text: str, evidence: list[str] | None = None) -> str:
        return rewrite_keep_grounding(text, evidence)

    @classmethod
    def format_pnl(cls, holdings: list[dict[str, Any]], nav: float | None = None) -> str:
        return format_pnl_table(holdings, nav)


__all__ = [
    "OutputGuardrail",
    "GuardrailResult",
    "DEFAULT_DISCLAIMER",
    "find_buy_sell_phrases",
    "mask_structural_numbers",
    "check_output",
    "strip_buy_sell",
    "rewrite_keep_grounding",
    "format_pnl_table",
    "has_evidence_grounding",
    "check_rewrite_grounding",
]
