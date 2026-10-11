"""CORS resolution middleware utilities."""

from __future__ import annotations


def resolve_cors_origins(frontend_origin: str | None) -> list[str]:
    """Phân giải cấu hình CORS: `*` hoặc rỗng cho phép mọi origin; ngược lại trả về origin cụ thể."""
    value = (frontend_origin or "*").strip() or "*"
    if value == "*":
        return ["*"]
    return [value]
