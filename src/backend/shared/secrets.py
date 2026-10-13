"""Đọc secret lúc chạy. Cờ tắt thì dùng .env. Cờ bật thì hỏi Secret Manager."""

from __future__ import annotations

import os
from typing import Any, Protocol

RUNTIME_SECRET_FIELDS = {
    "OPENAI_API_KEYS": "openai_api_keys",
    "LANGFUSE_PUBLIC_KEY": "langfuse_public_key",
    "LANGFUSE_SECRET_KEY": "langfuse_secret_key",
}


class SecretClient(Protocol):
    def access_secret(self, name: str) -> str: ...


def _enabled(target: Any | None = None) -> bool:
    if target is not None:
        return bool(getattr(target, "use_secret_manager", False))
    from backend.shared.settings import settings

    return bool(settings.use_secret_manager)


def build_secret_manager_client() -> SecretClient | None:
    """Tạo client GCP. Thiếu project hoặc thư viện thì trả None, không làm app sập."""
    project = os.environ.get("GCP_PROJECT_ID", "").strip()
    if not project:
        return None
    try:
        from google.cloud import secretmanager
    except ImportError:
        return None
    try:
        gcp = secretmanager.SecretManagerServiceClient()
    except Exception:
        return None

    class _Client:
        def access_secret(self, name: str) -> str:
            path = f"projects/{project}/secrets/{name}/versions/latest"
            response = gcp.access_secret_version(request={"name": path})
            return response.payload.data.decode("utf-8")

    return _Client()


def _read_manager(name: str, client: SecretClient | None) -> str | None:
    if client is None:
        return None
    try:
        value = client.access_secret(name)
    except Exception:
        return None
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def get_secret(name: str, client: SecretClient | None = None) -> str | None:
    """Cờ tắt: đọc môi trường. Cờ bật: Secret Manager, lỗi thì giữ .env."""
    if not _enabled():
        return os.environ.get(name)
    if client is None:
        client = build_secret_manager_client()
    managed = _read_manager(name, client)
    if managed:
        return managed
    return os.environ.get(name)


def apply_runtime_secrets(
    target: Any | None = None,
    client: SecretClient | None = None,
) -> dict[str, str]:
    """Ghi đè ba secret lên settings khi cờ bật. Trả các giá trị lấy từ Secret Manager."""
    from backend.shared.settings import settings as default_settings

    current = target if target is not None else default_settings
    if not _enabled(current):
        return {}
    if client is None:
        client = build_secret_manager_client()
    applied: dict[str, str] = {}
    for secret_name, field_name in RUNTIME_SECRET_FIELDS.items():
        managed = _read_manager(secret_name, client)
        if not managed:
            continue
        setattr(current, field_name, managed)
        applied[secret_name] = managed
    return applied
