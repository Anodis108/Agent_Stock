"""Chuẩn hoá steps[] one-shot (contract test-plan / timeline UI)."""

from __future__ import annotations

from typing import Any

_ALLOWED_STATUS = frozenset({"pending", "running", "done", "error"})


def normalize_steps(raw: Any) -> list[dict[str, Any]]:
    """Trả list `{id, name, status, detail?, input?, output?}` — thiếu field thì điền mặc định."""
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for i, item in enumerate(raw, start=1):
        if not isinstance(item, dict):
            continue
        sid = str(item.get("id") or i)
        name = str(item.get("name") or item.get("tool") or f"step_{i}")
        status = str(item.get("status") or "done").lower()
        if status not in _ALLOWED_STATUS:
            status = "done"
        detail = item.get("detail")
        if detail is not None:
            detail = str(detail)
        step: dict[str, Any] = {"id": sid, "name": name, "status": status}
        if "duration_s" in item and item["duration_s"] is not None:
            step["duration_s"] = round(float(item["duration_s"]), 3)
        if "duration_ms" in item and item["duration_ms"] is not None:
            step["duration_ms"] = int(item["duration_ms"])
        elif "duration_s" in step:
            step["duration_ms"] = int(round(step["duration_s"] * 1000))
        if detail is not None:
            step["detail"] = detail
        if "input" in item and item["input"] is not None:
            step["input"] = item["input"]
        if "output" in item and item["output"] is not None:
            step["output"] = item["output"]
        out.append(step)
    return out


def mark_mid_run_error(
    steps: list[dict[str, Any]] | None,
    *,
    detail: str | None = None,
    failed_name: str | None = None,
) -> list[dict[str, Any]]:
    """Đánh `error` lên bước lỗi giữa chừng; giữ các bước done trước đó.

    - Nếu có `failed_name`: đánh bước trùng name đầu tiên.
    - Else: đánh bước `running`/`pending` đầu tiên.
    - Else: đánh bước cuối; nếu list rỗng → thêm bước `error`.
    """
    out = [dict(s) for s in (steps or [])]
    msg = (detail or "lỗi giữa chừng").strip() or "lỗi giữa chừng"

    if failed_name:
        for s in out:
            if s.get("name") == failed_name:
                s["status"] = "error"
                s["detail"] = msg
                return out

    for s in out:
        if s.get("status") in ("running", "pending"):
            s["status"] = "error"
            s["detail"] = msg
            return out

    if out:
        # Đã có bước error → giữ; không thì đánh bước cuối
        if any(s.get("status") == "error" for s in out):
            return out
        out[-1]["status"] = "error"
        out[-1]["detail"] = msg
        return out

    return [{"id": "1", "name": "request", "status": "error", "detail": msg}]


def ensure_steps_reflect_error(
    steps: list[dict[str, Any]] | None,
    *,
    error: Any = None,
) -> list[dict[str, Any]]:
    """Nếu payload có `error` (string) mà chưa có bước error → đánh giữa chừng."""
    normalized = normalize_steps(steps)
    if any(s.get("status") == "error" for s in normalized):
        return normalized
    err_text = str(error).strip() if error not in (None, "") else ""
    if not err_text:
        return normalized
    return mark_mid_run_error(normalized, detail=err_text)
