"""Tests for Web Backend chart serving (Local disk & MinIO Object Storage)."""

from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from common.storage import ChartObjectStore, reset_chart_store
from web_backend.main import app, charts_path


class FakeMinioForWeb:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def bucket_exists(self, bucket: str) -> bool:
        return True

    def get_object(self, bucket: str, name: str):
        if name not in self.objects:
            raise KeyError(name)
        data = self.objects[name]

        class _Stream:
            def read(self) -> bytes:
                return data

        return _Stream()


@pytest.fixture
def client():
    return TestClient(app)


def test_get_chart_from_local_disk(client: TestClient, tmp_path: Path, monkeypatch):
    """Kiểm tra GET /charts/{name} trả ảnh thành công từ đĩa cục bộ."""
    test_img = b"\x89PNG\r\n\x1a\nlocal_img_data"
    test_file = charts_path / "chart_unit_test.png"
    test_file.write_bytes(test_img)

    try:
        resp = client.get("/charts/chart_unit_test.png")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "image/png"
        assert resp.content == test_img
    finally:
        if test_file.is_file():
            test_file.unlink()


def test_get_chart_from_minio_object_storage(client: TestClient, monkeypatch):
    """Kiểm tra GET /charts/{name} đọc từ MinIO khi tệp không có trên đĩa."""
    fake_minio = FakeMinioForWeb()
    test_img = b"\x89PNG\r\n\x1a\nminio_img_data"
    fake_minio.objects["chart_minio_only.png"] = test_img

    mock_store = ChartObjectStore(client=fake_minio, bucket="charts")
    monkeypatch.setattr("common.storage.get_chart_store", lambda: mock_store)

    resp = client.get("/charts/chart_minio_only.png")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"
    assert resp.content == test_img

    # Cũng kiểm tra qua đường dẫn alias /static/charts/...
    resp_static = client.get("/static/charts/chart_minio_only.png")
    assert resp_static.status_code == 200
    assert resp_static.content == test_img


def test_get_chart_not_found(client: TestClient, monkeypatch):
    """Kiểm tra GET /charts/{name} trả 404 khi ảnh không tồn tại ở cả đĩa và MinIO."""
    fake_minio = FakeMinioForWeb()
    mock_store = ChartObjectStore(client=fake_minio, bucket="charts")
    monkeypatch.setattr("common.storage.get_chart_store", lambda: mock_store)

    resp = client.get("/charts/non_existent_chart.png")
    assert resp.status_code == 404


def test_get_chart_invalid_filename(client: TestClient):
    """Kiểm tra GET /charts/{name} trả 400 khi tên tệp không hợp lệ."""
    resp = client.get("/charts/not_a_png.txt")
    assert resp.status_code == 400


def test_web_health_contains_storage_and_database(client: TestClient):
    """Kiểm tra endpoint /health chứa thông tin database và storage backend."""
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "database" in data
    assert "storage" in data
    assert "backend" in data["storage"]
