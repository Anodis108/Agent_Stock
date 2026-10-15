"""Chart PNG lên MinIO. Không cần server MinIO."""

from __future__ import annotations

import io
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from ai_backend.infra.agents.chart_agent import _save_and_encode_fig
from ai_backend.infra.storage.chart_store import (
    ChartObjectStore,
    read_chart_png,
    reset_chart_store,
    safe_png_name,
)
from common.settings import settings


class _Body:
    def __init__(self, data: bytes) -> None:
        self._data = data

    def read(self) -> bytes:
        return self._data

    def close(self) -> None:
        return None

    def release_conn(self) -> None:
        return None


class _FakeMinio:
    def __init__(self) -> None:
        self.buckets: set[str] = set()
        self.objects: dict[tuple[str, str], bytes] = {}

    def bucket_exists(self, bucket: str) -> bool:
        return bucket in self.buckets

    def make_bucket(self, bucket: str) -> None:
        self.buckets.add(bucket)

    def put_object(self, bucket: str, name: str, stream: io.BytesIO, length: int, content_type: str) -> None:
        self.objects[(bucket, name)] = stream.read(length)

    def get_object(self, bucket: str, name: str) -> _Body:
        return _Body(self.objects[(bucket, name)])


def test_safe_png_name_rejects_path_traversal():
    assert safe_png_name("chart_FPT_ab.png") == "chart_FPT_ab.png"
    assert safe_png_name("../chart_FPT_ab.png") == "chart_FPT_ab.png"
    assert safe_png_name("chart_FPT_ab.txt") is None
    assert safe_png_name("") is None


def test_put_and_get_roundtrip():
    fake = _FakeMinio()
    store = ChartObjectStore(client=fake, bucket="charts")
    png = b"\x89PNG\r\n\x1a\n" + b"x" * 20
    ref = store.put("chart_FPT_ab.png", png)
    assert ref == "minio://charts/chart_FPT_ab.png"
    assert fake.buckets == {"charts"}
    assert store.get("chart_FPT_ab.png") == png
    assert store.get("missing.png") is None


def test_default_save_uploads_when_store_ready(monkeypatch):
    fake = _FakeMinio()
    store = ChartObjectStore(client=fake, bucket="charts")
    monkeypatch.setattr("ai_backend.infra.storage.chart_store.get_chart_store", lambda: store)

    fig = plt.figure(figsize=(2, 1))
    fig.add_subplot(111).plot([1, 2, 3])
    file_path, file_name, url, base64_uri = _save_and_encode_fig(fig, "unit01")
    plt.close(fig)

    assert file_path == f"minio://charts/{file_name}"
    assert url == f"/charts/{file_name}"
    assert base64_uri.startswith("data:image/png;base64,")
    stored = store.get(file_name)
    assert stored is not None and stored[:8] == b"\x89PNG\r\n\x1a\n"


def test_explicit_output_dir_stays_on_disk(tmp_path: Path, monkeypatch):
    def _boom():
        raise AssertionError("không được gọi MinIO khi có output_dir")

    monkeypatch.setattr("ai_backend.infra.storage.chart_store.get_chart_store", _boom)
    fig = plt.figure(figsize=(2, 1))
    fig.add_subplot(111).plot([1, 2])
    file_path, file_name, url, _ = _save_and_encode_fig(fig, "disk01", output_dir=tmp_path)
    plt.close(fig)

    assert url == f"/charts/{file_name}"
    assert Path(file_path).is_file()
    assert Path(file_path).stat().st_size > 100


def test_read_chart_png_uses_disk_when_minio_off(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(settings, "chart_backend", "local")
    reset_chart_store()
    monkeypatch.setattr(
        "ai_backend.shared.charts.get_charts_dir",
        lambda: tmp_path,
    )
    (tmp_path / "chart_local.png").write_bytes(b"\x89PNG\r\n\x1a\nlocal")
    try:
        assert read_chart_png("chart_local.png") == b"\x89PNG\r\n\x1a\nlocal"
        assert read_chart_png("../secret.png") is None
    finally:
        reset_chart_store()
