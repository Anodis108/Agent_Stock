"""Language check — Class 7 slide 26: output đúng ngôn ngữ yêu cầu (tiếng Việt)."""

from __future__ import annotations

import re

_LATIN = re.compile(r"[A-Za-zÀ-ỹ]")
_VI_DIACRITIC = re.compile(
    r"[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]",
    re.IGNORECASE,
)
_VI_WORDS = (
    "giá", "tin", "cổ", "phiếu", "tăng", "giảm", "phiên", "mã", "không",
    "và", "của", "là", "có", "đã", "theo", "với", "cho", "này", "khớp",
    "tiêu", "cực", "tích", "lịch", "sử", "chờ", "duyệt", "xin", "lỗi",
)


def looks_vietnamese(text: str) -> bool:
    """True nếu có dấu tiếng Việt, từ khóa VN, hoặc gần như không có chữ Latin (số/mã)."""
    blob = (text or "").strip()
    if not blob:
        return False
    if _VI_DIACRITIC.search(blob):
        return True
    low = blob.lower()
    if any(w in low for w in _VI_WORDS):
        return True
    return not _LATIN.search(blob)
