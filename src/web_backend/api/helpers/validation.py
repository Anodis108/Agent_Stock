"""API input validation — 4xx rõ ràng, không 500."""

from __future__ import annotations

import re

from fastapi import HTTPException

# Mã CK VN: chữ cái (có thể kèm số như E1VFVN30 rút gọn), 2–10 ký tự
_SYMBOL_RE = re.compile(r"^[A-Z0-9]{2,10}$")


def normalize_symbol(raw: str | None) -> str:
    sym = (raw or "").strip().upper()
    if not sym:
        raise HTTPException(status_code=400, detail="symbol rỗng")
    if not _SYMBOL_RE.fullmatch(sym):
        raise HTTPException(
            status_code=400,
            detail="symbol không hợp lệ (chỉ chữ/số, 2–10 ký tự)",
        )
    return sym


def normalize_question(raw: str | None) -> str:
    q = (raw or "").strip()
    if not q:
        raise HTTPException(status_code=400, detail="câu hỏi rỗng")
    return q


def title_from_question(q: str, max_len: int = 40) -> str:
    cleaned = " ".join(q.strip().split())
    if len(cleaned) <= max_len:
        return cleaned
    return cleaned[:max_len].rstrip() + "..."


def validate_threshold_pct(value: float | None, *, required: bool = False) -> float | None:
    if value is None:
        if required:
            raise HTTPException(status_code=400, detail="ngưỡng không hợp lệ")
        return None
    try:
        thr = float(value)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="ngưỡng không hợp lệ") from exc
    if thr < 0:
        raise HTTPException(status_code=400, detail="ngưỡng không được âm")
    return thr


def normalize_approval_id(raw: str | None) -> str:
    aid = (raw or "").strip()
    if not aid:
        raise HTTPException(status_code=400, detail="approval_id rỗng")
    return aid


def normalize_reject_reason(raw: str | None) -> str:
    why = (raw or "").strip()
    if not why:
        raise HTTPException(status_code=400, detail="lý do reject rỗng")
    return why
