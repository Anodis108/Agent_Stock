"""Concepts router — POST /v1/concepts/ingest (multipart file only)."""

from __future__ import annotations

import re

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile

from ai_backend.application.concept_ingestion_service import (
    ConceptIngestionInput,
    ConceptIngestionOutput,
    ConceptIngestionService,
)
from ai_backend.shared.logging import get_logger

logger = get_logger("ai_backend.api.concepts")

router = APIRouter(prefix="/v1/concepts", tags=["concepts"])

_FILENAME_PATTERN = re.compile(r"^[a-z0-9-]+\.md$")


def _get_service(request: Request) -> ConceptIngestionService:
    service = getattr(request.app.state, "concept_ingestion_service", None)
    if service is not None:
        return service
    return ConceptIngestionService()


@router.post("/ingest", response_model=ConceptIngestionOutput, summary="Tải lên tệp markdown khái niệm")
async def ingest_concepts(
    request: Request,
    file: UploadFile = File(..., description="Tệp markdown [a-z0-9-]+.md"),
    collection_name: str | None = Form(default=None, description="Qdrant collection (tùy chọn)"),
) -> ConceptIngestionOutput:
    """Nhận duy nhất một file markdown; lưu vào resources/docs/concepts và reindex Qdrant."""
    try:
        filename = (file.filename or "").strip()
        content_bytes = await file.read()
        content_str = content_bytes.decode("utf-8")

        service = _get_service(request)
        coll_str = collection_name.strip() if collection_name else None
    except Exception as exc:
        logger.error(f"Lỗi nạp tệp khái niệm: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Lỗi hệ thống khi nạp tệp: {exc}") from exc
    
    try:
        input = ConceptIngestionInput(
            filename=filename,
            content=content_str,
            collection_name=coll_str,
        )
        return service.process(input)
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err
    except Exception as exc:
        logger.error(f"Lỗi nạp tệp khái niệm: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Lỗi hệ thống khi nạp tệp: {exc}") from exc
