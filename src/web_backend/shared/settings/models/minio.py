from __future__ import annotations

from common.base.base_model import CustomBaseModel


class MinioSettings(CustomBaseModel):
    """Cấu hình kết nối MinIO Object Storage."""

    endpoint: str | None = None
    bucket: str | None = None
    access_key: str | None = None
    secret_key: str | None = None
    secure: bool | None = None
