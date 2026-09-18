"""CORS origins từ FRONTEND_ORIGIN — tách hàm để test không reload app."""

from __future__ import annotations


def resolve_cors_origins(frontend_origin: str | None) -> list[str]:
    """`*` hoặc rỗng → mọi origin (dev); ngược lại một origin cụ thể."""
    value = (frontend_origin or "*").strip() or "*"
    if value == "*":
        return ["*"]
    return [value]
