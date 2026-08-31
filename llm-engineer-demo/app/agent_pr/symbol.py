"""Chuẩn hoá mã CP VN — không whitelist vài mã.

HOSE/HNX/UPCOM: thường 3 chữ (HPG, VNM). ETF/CW dài hơn. Chỉ chặn chuỗi
rỗng / ký tự lạ — vnstock/CafeF tự trả rỗng nếu mã không tồn tại.
"""

from __future__ import annotations

import re

_TICKER = re.compile(r"^[A-Z0-9]{3,10}$")


def normalize_symbol(raw: str) -> str:
    """Upper + strip. Raise ValueError nếu không giống mã niêm yết VN."""
    symbol = str(raw or "").strip().upper()
    if not _TICKER.match(symbol):
        raise ValueError(f"Mã '{raw}' không hợp lệ")
    return symbol
