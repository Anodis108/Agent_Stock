from __future__ import annotations

from common.base.base_model import CustomBaseModel


class RedisSettings(CustomBaseModel):
    """Cấu hình kết nối Redis Cache & Memory."""

    url: str | None = None
    host: str | None = None
    port: int | None = None
    password: str | None = None
