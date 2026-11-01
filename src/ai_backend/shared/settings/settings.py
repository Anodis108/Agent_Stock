"""Cấu hình AI Backend — CHỈ đọc từ biến môi trường (mặc định mọi trường là None)."""

from __future__ import annotations

import json
import os

import common.settings.config  # noqa: F401 — nạp .env thành biến môi trường khi chạy local
from ai_backend.shared.settings.models import MinioSettings, QdrantSettings, RedisSettings
from common.base.base_model import CustomBaseModel


class AiSettings(CustomBaseModel):
    """Cấu hình microservice AI Backend (Cổng 8001)."""

    app_name: str | None = None
    version: str | None = None
    host: str | None = None
    port: int | None = None

    # Nested Settings models
    qdrant: QdrantSettings | None = None
    redis: RedisSettings | None = None
    minio: MinioSettings | None = None

    # Qdrant Vector Store (flat fields for backward compatibility)
    qdrant_url: str | None = None
    qdrant_host: str | None = None
    qdrant_port: int | None = None
    qdrant_api_key: str | None = None
    qdrant_collection: str | None = None

    # Redis Cache & Memory (flat fields for backward compatibility)
    redis_url: str | None = None
    redis_host: str | None = None
    redis_port: int | None = None
    redis_password: str | None = None

    # LLM Settings & Keys
    openai_api_key: str | None = None
    openai_base_url: str | None = None
    llm_backend: str | None = None
    llm_model: str | None = None
    llm_temperature: float | None = None
    llm_timeout: float | None = None

    # Safety
    input_guardrails_enabled: bool | None = None
    output_guardrails_enabled: bool | None = None
    exact_cache_enabled: bool | None = None
    semantic_cache_enabled: bool | None = None

    # Database & Storage
    database_url: str | None = None
    charts_dir: str | None = None
    chart_backend: str | None = None
    minio_endpoint: str | None = None
    minio_bucket: str | None = None
    minio_access_key: str | None = None
    minio_secret_key: str | None = None
    minio_secure: bool | None = None
    log_level: str | None = None
    cors_origins: list[str] | None = None

    # Scan: ngưỡng % biến động giá mặc định khi API/watchlist không truyền (mode=scan).
    scan_default_threshold_pct: float | None = None

    @classmethod
    def load(cls) -> AiSettings:
        """Mỗi trường đọc đúng một biến môi trường; không có thì để None."""
        env_names = {
            "app_name": "AI_APP_NAME",
            "version": "AI_VERSION",
            "host": "AI_HOST",
            "port": "AI_PORT",
            "qdrant_url": "QDRANT_URL",
            "qdrant_host": "QDRANT_HOST",
            "qdrant_port": "QDRANT_PORT",
            "qdrant_api_key": "QDRANT_API_KEY",
            "qdrant_collection": "QDRANT_COLLECTION",
            "redis_url": "REDIS_URL",
            "redis_host": "REDIS_HOST",
            "redis_port": "REDIS_PORT",
            "redis_password": "REDIS_PASSWORD",
            "openai_api_key": "OPENAI_API_KEY",
            "openai_base_url": "OPENAI_BASE_URL",
            "llm_backend": "LLM_BACKEND",
            "llm_model": "LLM_MODEL",
            "llm_temperature": "LLM_TEMPERATURE",
            "llm_timeout": "LLM_TIMEOUT",
            "input_guardrails_enabled": "INPUT_GUARDRAILS_ENABLED",
            "output_guardrails_enabled": "OUTPUT_GUARDRAILS_ENABLED",
            "exact_cache_enabled": "EXACT_CACHE_ENABLED",
            "semantic_cache_enabled": "SEMANTIC_CACHE_ENABLED",
            "database_url": "DATABASE_URL",
            "charts_dir": "CHARTS_DIR",
            "chart_backend": "CHART_BACKEND",
            "minio_endpoint": "MINIO_ENDPOINT",
            "minio_bucket": "MINIO_BUCKET",
            "minio_access_key": "MINIO_ACCESS_KEY",
            "minio_secret_key": "MINIO_SECRET_KEY",
            "minio_secure": "MINIO_SECURE",
            "log_level": "LOG_LEVEL",
            "cors_origins": "CORS_ORIGINS",
            "scan_default_threshold_pct": "AI_SCAN_DEFAULT_THRESHOLD_PCT",
        }
        values = {field: os.environ.get(name) for field, name in env_names.items() if os.environ.get(name)}
        if "cors_origins" in values:
            values["cors_origins"] = json.loads(values["cors_origins"])  # JSON, vd. ["*"]
        if "scan_default_threshold_pct" in values:
            values["scan_default_threshold_pct"] = float(values["scan_default_threshold_pct"])

        # Populate nested models from the same env values
        qdrant_values = {
            "url": values.get("qdrant_url"),
            "host": values.get("qdrant_host"),
            "port": int(values["qdrant_port"]) if values.get("qdrant_port") else None,
            "api_key": values.get("qdrant_api_key"),
            "collection": values.get("qdrant_collection"),
        }
        if any(v is not None for v in qdrant_values.values()):
            values["qdrant"] = QdrantSettings(**qdrant_values)

        redis_values = {
            "url": values.get("redis_url"),
            "host": values.get("redis_host"),
            "port": int(values["redis_port"]) if values.get("redis_port") else None,
            "password": values.get("redis_password"),
        }
        if any(v is not None for v in redis_values.values()):
            values["redis"] = RedisSettings(**redis_values)

        minio_values = {
            "endpoint": values.get("minio_endpoint"),
            "bucket": values.get("minio_bucket"),
            "access_key": values.get("minio_access_key"),
            "secret_key": values.get("minio_secret_key"),
            "secure": values["minio_secure"].lower() in ("true", "1", "yes") if values.get("minio_secure") else None,
        }
        if any(v is not None for v in minio_values.values()):
            values["minio"] = MinioSettings(**minio_values)

        return cls(**values)


ai_settings = AiSettings.load()
settings = ai_settings
