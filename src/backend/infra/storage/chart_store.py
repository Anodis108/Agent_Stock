"""MinIO / Local Object Store for Charts."""
from __future__ import annotations

import io
from pathlib import Path
from typing import Any

import backend.shared.charts as backend_charts
from backend.shared.settings import settings

_STORE: ChartObjectStore | None = None


def safe_png_name(name: str) -> str | None:
    if not name:
        return None
    cleaned = Path(name).name
    if not cleaned.lower().endswith(".png"):
        return None
    return cleaned


class ChartObjectStore:
    def __init__(self, client: Any = None, bucket: str = "charts") -> None:
        self.client = client
        self.bucket = bucket
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        if self.client is not None:
            try:
                if hasattr(self.client, "bucket_exists") and not self.client.bucket_exists(self.bucket):
                    self.client.make_bucket(self.bucket)
            except Exception:
                pass

    def put(self, name: str, data: bytes) -> str:
        safe_name = safe_png_name(name) or name
        self._ensure_bucket()
        if self.client is not None:
            stream = io.BytesIO(data)
            self.client.put_object(
                self.bucket,
                safe_name,
                stream,
                len(data),
                "image/png",
            )
        return f"minio://{self.bucket}/{safe_name}"

    def get(self, name: str) -> bytes | None:
        safe_name = safe_png_name(name)
        if not safe_name or self.client is None:
            return None
        try:
            resp = self.client.get_object(self.bucket, safe_name)
            return resp.read()
        except Exception:
            return None


def get_chart_store() -> ChartObjectStore | None:
    global _STORE
    if getattr(settings, "chart_backend", "local") != "minio":
        return None
    if _STORE is None:
        try:
            from minio import Minio
            client = Minio(
                settings.minio_endpoint,
                access_key=settings.minio_access_key,
                secret_key=settings.minio_secret_key,
                secure=settings.minio_secure,
            )
            _STORE = ChartObjectStore(client=client, bucket=settings.minio_bucket)
        except Exception:
            return None
    return _STORE


def reset_chart_store() -> None:
    global _STORE
    _STORE = None


def read_chart_png(name: str) -> bytes | None:
    safe_name = safe_png_name(name)
    if not safe_name:
        return None
    store = get_chart_store()
    if store is not None:
        data = store.get(safe_name)
        if data is not None:
            return data
    path = backend_charts.get_charts_dir() / safe_name
    if path.is_file():
        return path.read_bytes()
    return None
