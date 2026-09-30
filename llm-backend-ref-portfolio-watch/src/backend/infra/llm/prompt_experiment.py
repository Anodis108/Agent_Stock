"""A/B prompt version selection — Module III Bài 1."""

from __future__ import annotations

import hashlib


def pick_prompt_version(
    user_id: str,
    *,
    enabled: bool = False,
    version_a: str = "v1",
    version_b: str = "v2",
    split_pct: int = 50,
) -> str:
    """Chọn phiên bản prompt theo bucket cố định theo user_id.

    Cùng user_id luôn nhận cùng variant (sticky bucket).
    """
    if not enabled:
        return version_a
    if split_pct <= 0:
        return version_a
    if split_pct >= 100:
        return version_b
    digest = hashlib.sha256(user_id.encode()).hexdigest()
    bucket = int(digest[:8], 16) % 100
    return version_b if bucket < split_pct else version_a
