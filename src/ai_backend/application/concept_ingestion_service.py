"""Concept Ingestion Service — Quản lý lưu trữ tệp và nạp chỉ mục khái niệm vào Qdrant.

Kế thừa BaseService từ common.base.base_service.
Nhận một tệp markdown (tên `[a-z0-9-]+.md`), lưu vào `resources/docs/concepts/` rồi reindex toàn bộ thư mục vào Qdrant.
"""

from __future__ import annotations

import re
from typing import Any, Callable

from pydantic import Field

from common.base.base_model import CustomBaseModel
from common.base.base_service import BaseService
from ai_backend.shared.logging import get_logger
from ai_backend.shared.settings import ai_settings
from ai_backend.infra.retrieval.concepts import (
    concepts_dir,
    index_concepts,
)

logger = get_logger("ai_backend.application.concept_ingestion")

_FILENAME_PATTERN = re.compile(r"^[a-z0-9-]+\.md$")


class ConceptIngestionInput(CustomBaseModel):
    """Đầu vào cho việc nạp hoặc đánh chỉ mục tài liệu khái niệm chứng khoán."""

    filename: str = Field(description="Tên tệp markdown (.md)")
    content: str = Field(description="Nội dung markdown UTF-8")
    collection_name: str | None = Field(default=None, description="Tên collection Qdrant mục tiêu")


class ConceptIngestionOutput(CustomBaseModel):
    """Kết quả phản hồi sau khi nạp / reindex khái niệm vào Qdrant."""

    points_written: int = Field(description="Số lượng vector point đã nạp vào Qdrant")
    files: list[str] = Field(default_factory=list, description="Danh sách các tệp khái niệm hiện có")


class ConceptIngestionService(BaseService):
    """Service điều phối lưu trữ và đánh chỉ mục tài liệu khái niệm vào Qdrant."""

    def __init__(
        self,
        *,
        client: Any = None,
        embed_fn: Callable[[list[str]], list[list[float]]] | None = None,
    ) -> None:
        self.client = client
        self.embed_fn = embed_fn

    def process(self, inputs: ConceptIngestionInput) -> ConceptIngestionOutput:
        """Lưu tệp tải lên và reindex toàn bộ tài liệu khái niệm vào Qdrant."""
        fn = inputs.filename.strip()
        if not _FILENAME_PATTERN.match(fn):
            raise ValueError(
                f"Tên tệp '{fn}' không hợp lệ. Chỉ chấp nhận chữ thường, số, dấu gạch ngang và đuôi .md ([a-z0-9-]+\\.md)"
            )
        if not inputs.content.strip():
            raise ValueError("Nội dung tệp markdown không được để trống.")

        target_path = concepts_dir() / fn
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(inputs.content, encoding="utf-8")
        logger.info(f"Đã lưu tệp khái niệm: {target_path.name}")

        # Chuẩn bị Qdrant client
        client = self.client
        if client is None:
            from ai_backend.infra.storage.long_term_memory import get_qdrant_client

            client = get_qdrant_client(url=ai_settings.qdrant_url)
        if client is None:
            raise RuntimeError("Không thể kết nối tới Qdrant client để đánh chỉ mục khái niệm.")

        # 3. Tiến hành reindex collection
        coll_name = (
            inputs.collection_name
            or getattr(ai_settings, "concept_collection", "stock_concepts")
        )
        logger.info(f"Tiến hành reindex tài liệu khái niệm vào Qdrant collection '{coll_name}'")

        points_written = index_concepts(
            client=client,
            collection_name=coll_name,
            embed_fn=self.embed_fn,
        )

        all_files = sorted([p.name for p in concepts_dir().glob("*.md")])
        logger.info(f"Reindex hoàn tất: ghi nhận {points_written} points từ {len(all_files)} tệp")

        return ConceptIngestionOutput(
            points_written=points_written,
            files=all_files,
        )
