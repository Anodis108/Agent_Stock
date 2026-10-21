"""Cấu hình Web Backend — CHỈ đọc từ biến môi trường (mặc định mọi trường là None)."""

from __future__ import annotations

import json
import os

from common.base.base_model import CustomBaseModel
import common.settings.config  # noqa: F401 — nạp .env thành biến môi trường khi chạy local


class WebSettings(CustomBaseModel):
    """Cấu hình microservice Web Backend (Cổng 8000)."""

    app_name: str | None = None
    version: str | None = None
    host: str | None = None
    port: int | None = None
    ai_base_url: str | None = None
    ai_http_timeout: float | None = None
    database_url: str | None = None
    log_level: str | None = None
    frontend_origin: str | None = None
    cors_origins: list[str] | None = None
    default_alert_threshold_pct: float | None = None
    charts_dir: str | None = None
    chart_backend: str | None = None
    minio_endpoint: str | None = None
    minio_bucket: str | None = None
    minio_access_key: str | None = None
    minio_secret_key: str | None = None
    minio_secure: bool | None = None

    @classmethod
    def load(cls) -> WebSettings:
        """Mỗi trường đọc đúng một biến môi trường; không có thì để None."""
        env_names = {
            "app_name": "WEB_APP_NAME",
            "version": "WEB_VERSION",
            "host": "API_HOST",
            "port": "API_PORT",
            "ai_base_url": "AI_BASE_URL",
            "ai_http_timeout": "AI_HTTP_TIMEOUT",
            "database_url": "DATABASE_URL",
            "log_level": "LOG_LEVEL",
            "frontend_origin": "FRONTEND_ORIGIN",
            "cors_origins": "CORS_ORIGINS",
            "default_alert_threshold_pct": "DEFAULT_ALERT_THRESHOLD_PCT",
            "charts_dir": "CHARTS_DIR",
            "chart_backend": "CHART_BACKEND",
            "minio_endpoint": "MINIO_ENDPOINT",
            "minio_bucket": "MINIO_BUCKET",
            "minio_access_key": "MINIO_ACCESS_KEY",
            "minio_secret_key": "MINIO_SECRET_KEY",
            "minio_secure": "MINIO_SECURE",
        }
        values = {field: os.environ.get(name) for field, name in env_names.items() if os.environ.get(name)}
        if "cors_origins" in values:
            values["cors_origins"] = json.loads(values["cors_origins"])  # JSON, vd. ["*"]
        return cls(**values)


web_settings = WebSettings.load()
settings = web_settings
