"""Kiểm thử Concept Ingestion — POST /v1/concepts/ingest (file only)."""

from __future__ import annotations

import io

import pytest
from fastapi.testclient import TestClient
from qdrant_client import QdrantClient

from ai_backend.application.concept_ingestion_service import (
    ConceptIngestionInput,
    ConceptIngestionOutput,
    ConceptIngestionService,
)
from ai_backend.infra.retrieval.concepts import concepts_dir, embed_concept_texts
from ai_backend.main import app
from common.base.base_service import BaseService


@pytest.fixture
def in_memory_client() -> QdrantClient:
    return QdrantClient(":memory:")


@pytest.fixture
def ingestion_service(in_memory_client: QdrantClient) -> ConceptIngestionService:
    return ConceptIngestionService(
        client=in_memory_client,
        embed_fn=embed_concept_texts,
    )


class TestConceptIngestionService:
    def test_subclass_of_base_service(self):
        assert issubclass(ConceptIngestionService, BaseService)

    def test_save_and_reindex_new_file(self, ingestion_service: ConceptIngestionService):
        test_fn = "test-temp-ingest-unit.md"
        test_path = concepts_dir() / test_fn
        try:
            out = ingestion_service.process(
                ConceptIngestionInput(
                    filename=test_fn,
                    content="# Khái niệm thử nghiệm\n\nĐây là nội dung thử nghiệm nạp concept.",
                    collection_name="test_concepts",
                )
            )
            assert isinstance(out, ConceptIngestionOutput)
            assert out.points_written > 0
            assert test_fn in out.files
            assert test_path.exists()
        finally:
            if test_path.exists():
                test_path.unlink()

    def test_invalid_filename_rejected(self, ingestion_service: ConceptIngestionService):
        for name in ("RSI_and_SMA.md", "invalid.txt"):
            with pytest.raises(ValueError, match="không hợp lệ"):
                ingestion_service.process(
                    ConceptIngestionInput(
                        filename=name,
                        content="# Nội dung",
                        collection_name="test_concepts",
                    )
                )


class TestConceptIngestApi:
    @pytest.fixture(autouse=True)
    def setup_app_state(self, in_memory_client: QdrantClient):
        old_svc = getattr(app.state, "concept_ingestion_service", None)
        app.state.concept_ingestion_service = ConceptIngestionService(
            client=in_memory_client,
            embed_fn=embed_concept_texts,
        )
        yield
        if old_svc is not None:
            app.state.concept_ingestion_service = old_svc

    def test_post_without_file_returns_422(self):
        client = TestClient(app)
        assert client.post("/v1/concepts/ingest").status_code == 422

    def test_upload_file(self):
        test_fn = "test-api-multipart-ingest.md"
        test_path = concepts_dir() / test_fn
        client = TestClient(app)
        try:
            files = {
                "file": (
                    test_fn,
                    io.BytesIO(b"# MACD\n\nChi bao MACD."),
                    "text/markdown",
                )
            }
            resp = client.post("/v1/concepts/ingest", files=files)
            assert resp.status_code == 200
            data = resp.json()
            assert test_fn in data["files"]
            assert data["points_written"] > 0
            assert test_path.exists()
        finally:
            if test_path.exists():
                test_path.unlink()

    def test_invalid_filename_returns_400(self):
        client = TestClient(app)
        files = {"file": ("bad_name.txt", io.BytesIO(b"# Test"), "text/plain")}
        resp = client.post("/v1/concepts/ingest", files=files)
        assert resp.status_code == 400
