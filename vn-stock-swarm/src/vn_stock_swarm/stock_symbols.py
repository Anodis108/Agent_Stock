"""Danh sách mã cổ phiếu (HOSE/HNX/UPCOM) + khớp từ khoá — nền tảng cho việc
gắn 1 mẩu tin/1 câu hỏi với đúng mã cổ phiếu đang nói tới.
"""

from __future__ import annotations

import re

# Tập mã demo (HOSE/HNX/UPCOM), mỗi mã kèm các bí danh (alias) mà tiêu đề tin
# hay dùng thay vì gõ thẳng mã (tiếng Việt có dấu + không dấu + tiếng Anh).
# Không đầy đủ — mở rộng khi cần; văn bản không khớp được đơn giản rơi vào sink
# "news_general" (xem sink_router.py) — đó là kết quả hợp lệ, không phải lỗi.
STOCK_SYMBOLS: dict[str, list[str]] = {
    "VNM": ["VNM", "Vinamilk"],
    "HPG": ["HPG", "Hòa Phát", "Hoa Phat"],
    "FPT": ["FPT"],
    "VCB": ["VCB", "Vietcombank"],
}

_ALIAS_TO_SYMBOL: dict[str, str] = {
    alias.lower(): symbol for symbol, aliases in STOCK_SYMBOLS.items() for alias in aliases
}

# Alias dài hơn xét trước để "Vietcombank" khớp trước khi 1 alias ngắn hơn
# (nếu có) từng là substring của nó khớp nhầm.
_ALIASES_BY_LENGTH = sorted(_ALIAS_TO_SYMBOL, key=len, reverse=True)


def match_symbols(text: str) -> list[str]:
    """Trả về mọi mã cổ phiếu có alias (từ khoá/tên công ty) xuất hiện trong ``text``.

    Giữ thứ tự xuất hiện, loại trùng. Trả về danh sách rỗng nếu không khớp gì
    — nơi gọi (SinkRouter, QueryCoordinator) coi đó là "tin chung" / "câu hỏi
    không nhắc mã nào", không phải là lỗi.
    """
    lowered = text.lower()
    found: list[str] = []
    for alias in _ALIASES_BY_LENGTH:
        if alias in lowered:
            symbol = _ALIAS_TO_SYMBOL[alias]
            if symbol not in found:
                found.append(symbol)
    return found


def extract_symbol_from_question(question: str) -> str | None:
    """Trích 1 mã cổ phiếu duy nhất từ câu hỏi cho QueryCoordinator (best-effort).

    Câu hỏi thường ngắn và chỉ hỏi về 1 mã tại 1 thời điểm, nên kết quả khớp
    đầu tiên chính là mã người dùng muốn hỏi. Có fallback bằng regex tìm mã
    viết hoa trần (vd "giá HPG" gõ không khớp verbatim với alias list) phòng
    khi có mã mới được hỏi trước khi stock_symbols.py kịp cập nhật.
    """
    matches = match_symbols(question)
    if matches:
        return matches[0]

    bare = re.search(r"\b[A-Z]{3}\b", question)
    return bare.group(0) if bare else None
