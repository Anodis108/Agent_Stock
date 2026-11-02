from __future__ import annotations

from common.base.base_model import CustomBaseModel


class QdrantSettings(CustomBaseModel):
    """Cấu hình kết nối Qdrant Vector Store."""

    url: str | None = None
    host: str | None = None
    port: int | None = None
    api_key: str | None = None
    collection: str | None = None
