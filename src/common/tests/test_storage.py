"""Tests for Common Storage Kernel (MinIO and disk fallback)."""

from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from common.storage import (
    ChartObjectStore,
    get_chart_store,
    get_default_charts_dir,
    read_chart_png,
    reset_chart_store,
    safe_png_name,
)


class FakeMinioClient:
    """Mock MinIO client for testing."""

    def __init__(self) -> None:
        self.buckets: set[str] = set()
        self.objects: dict[tuple[str, str], bytes] = {}

    def bucket_exists(self, bucket: str) -> bool:
        return bucket in self.buckets

    def make_bucket(self, bucket: str) -> None:
        self.buckets.add(bucket)

    def put_object(self, bucket: str, name: str, stream: io.BytesIO, length: int, content_type: str) -> None:
        self.objects[(bucket, name)] = stream.read(length)

    def get_object(self, bucket: str, name: str):
        if (bucket, name) not in self.objects:
            raise KeyError(name)
        data = self.objects[(bucket, name)]

        class _Stream:
            def read(self) -> bytes:
                return data

        return _Stream()


def test_safe_png_name_validation():
    """Đảm bảo safe_png_name lọc sạch path traversal và đuôi không phải .png."""
    assert safe_png_name("chart_fpt.png") == "chart_fpt.png"
    assert safe_png_name("../../chart_fpt.png") == "chart_fpt.png"
    assert safe_png_name("chart.jpg") is None
    assert safe_png_name("malicious.exe") is None
    assert safe_png_name("") is None


def test_chart_object_store_minio_put_and_get():
    """Kiểm tra lưu và đọc trực tiếp từ MinIO qua FakeMinioClient."""
    fake = FakeMinioClient()
    store = ChartObjectStore(client=fake, bucket="charts")
    assert store.is_connected() is True

    test_png = b"\x89PNG\r\n\x1a\n" + b"fakedata"
    ref = store.put("chart_fpt_01.png", test_png)
    assert ref == "minio://charts/chart_fpt_01.png"

    retrieved = store.get("chart_fpt_01.png")
    assert retrieved == test_png

    missing = store.get("non_existent.png")
    assert missing is None


def test_chart_object_store_disk_fallback_when_minio_absent(tmp_path: Path, monkeypatch):
    """Kiểm tra lưu và đọc từ đĩa cục bộ khi MinIO client không được cấu hình (None)."""
    monkeypatch.setattr("common.storage.minio_store.get_default_charts_dir", lambda: tmp_path)

    store = ChartObjectStore(client=None, bucket="charts")
    assert store.is_connected() is False

    test_png = b"\x89PNG\r\n\x1a\n" + b"localdata"
    ref = store.put("chart_fallback.png", test_png)
    assert ref == "minio://charts/chart_fallback.png"

    # File phải được ghi xuống đĩa cục bộ
    disk_file = tmp_path / "chart_fallback.png"
    assert disk_file.is_file()
    assert disk_file.read_bytes() == test_png

    # Đọc lại qua store.get
    assert store.get("chart_fallback.png") == test_png


def test_read_chart_png_integration(tmp_path: Path, monkeypatch):
    """Kiểm tra hàm tiện ích read_chart_png đọc đúng từ store hoặc đĩa."""
    reset_chart_store()
    monkeypatch.setattr("common.storage.minio_store.get_default_charts_dir", lambda: tmp_path)

    (tmp_path / "test_read.png").write_bytes(b"\x89PNG\r\n\x1a\nhello")
    data = read_chart_png("test_read.png")
    assert data == b"\x89PNG\r\n\x1a\nhello"

    # Tên không hợp lệ trả về None
    assert read_chart_png("invalid.txt") is None
