"""Unified Object Storage Kernel (MinIO with local disk fallback).

Provides direct access to MinIO object storage for both web_backend and ai_backend,
ensuring multi-container and distributed setups can access chart artifacts directly.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any

from common.logging import get_logger
from common.settings import settings

logger = get_logger(__name__)

_STORE: ChartObjectStore | None = None


def safe_png_name(name: str) -> str | None:
    """Validate and sanitize PNG file name, preventing path traversal attacks."""
    if not name:
        return None
    cleaned = Path(name).name
    if not cleaned.lower().endswith(".png"):
        return None
    return cleaned


def get_default_charts_dir() -> Path:
    """Return local directory used for chart disk storage."""
    configured = getattr(settings, "chart_dir", None)
    if configured:
        p = Path(configured)
        p.mkdir(parents=True, exist_ok=True)
        return p
    default_p = Path("resources/data/charts")
    default_p.mkdir(parents=True, exist_ok=True)
    return default_p


class ChartObjectStore:
    """Object store managing chart images on MinIO with local disk fallback."""

    def __init__(self, client: Any = None, bucket: str = "charts") -> None:
        self.client = client
        self.bucket = bucket
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        if self.client is not None:
            try:
                if hasattr(self.client, "bucket_exists") and not self.client.bucket_exists(self.bucket):
                    self.client.make_bucket(self.bucket)
            except Exception as exc:
                logger.debug("Failed to verify/create MinIO bucket '%s': %s", self.bucket, exc)

    def is_connected(self) -> bool:
        """Check if MinIO client is initialized and connected."""
        if self.client is None:
            return False
        try:
            if hasattr(self.client, "bucket_exists"):
                return bool(self.client.bucket_exists(self.bucket))
            return True
        except Exception:
            return False

    def put(self, name: str, data: bytes) -> str:
        """Upload image to MinIO. If MinIO is unavailable, write to local chart_dir."""
        safe_name = safe_png_name(name) or name
        self._ensure_bucket()

        minio_ok = False
        if self.client is not None:
            try:
                stream = io.BytesIO(data)
                self.client.put_object(
                    self.bucket,
                    safe_name,
                    stream,
                    len(data),
                    "image/png",
                )
                minio_ok = True
            except Exception as exc:
                logger.warning("MinIO put_object failed for '%s', writing to disk fallback: %s", safe_name, exc)

        # Always maintain local disk copy if MinIO write failed or for fast local serving
        if not minio_ok:
            try:
                disk_path = get_default_charts_dir() / safe_name
                disk_path.write_bytes(data)
            except Exception as exc:
                logger.error("Failed to write chart to local disk fallback: %s", exc)

        return f"minio://{self.bucket}/{safe_name}"

    def get(self, name: str) -> bytes | None:
        """Retrieve image bytes from MinIO, falling back to local disk if not found."""
        safe_name = safe_png_name(name)
        if not safe_name:
            return None

        # 1. Try MinIO first if client is configured
        if self.client is not None:
            try:
                resp = self.client.get_object(self.bucket, safe_name)
                data = resp.read()
                if data:
                    return data
            except Exception:
                pass

        # 2. Fall back to local disk
        disk_path = get_default_charts_dir() / safe_name
        if disk_path.is_file():
            try:
                return disk_path.read_bytes()
            except Exception:
                pass

        return None


def get_chart_store() -> ChartObjectStore | None:
    """Return singleton ChartObjectStore configured with real MinIO or local fallback."""
    global _STORE
    backend = getattr(settings, "chart_backend", "local")
    if backend != "minio":
        return None

    if _STORE is None:
        try:
            from minio import Minio

            endpoint = getattr(settings, "minio_endpoint", "localhost:9000")
            access_key = getattr(settings, "minio_access_key", "minioadmin")
            secret_key = getattr(settings, "minio_secret_key", "minioadmin")
            secure = bool(getattr(settings, "minio_secure", False))
            bucket = getattr(settings, "minio_bucket", "charts")

            client = Minio(
                endpoint,
                access_key=access_key,
                secret_key=secret_key,
                secure=secure,
            )
            _STORE = ChartObjectStore(client=client, bucket=bucket)
        except Exception as exc:
            logger.warning("Failed to initialize MinIO client: %s. Using local disk fallback.", exc)
            return None
    return _STORE


def reset_chart_store() -> None:
    """Reset singleton ChartObjectStore instance (useful in tests)."""
    global _STORE
    _STORE = None


def read_chart_png(name: str) -> bytes | None:
    """Read chart PNG data from MinIO or disk fallback."""
    safe_name = safe_png_name(name)
    if not safe_name:
        return None
    store = get_chart_store()
    if store is not None:
        data = store.get(safe_name)
        if data is not None:
            return data
    path = get_default_charts_dir() / safe_name
    if path.is_file():
        return path.read_bytes()
    return None
