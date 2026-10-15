"""Web Backend specific settings loaded from config.yaml and environment variables."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from common.base.base_model import CustomBaseModel
from common.settings.config import get_config_yaml_path, load_config_yaml_data


class WebSettings(CustomBaseModel):
    """Cấu hình microservice Web Backend (Cổng 8000)."""

    app_name: str = "VN Stock Swarm Web Gateway"
    version: str = "1.0.0"
    host: str = "0.0.0.0"
    port: int = 8000
    ai_base_url: str = "http://127.0.0.1:8001"
    ai_http_timeout: float = 60.0
    database_url: str | None = None
    sqlite_path: str = "resources/data/portfolio_watch.db"
    log_level: str = "INFO"
    frontend_origin: str = "*"
    cors_origins: list[str] = ["*"]
    default_alert_threshold_pct: float = 3.0
    charts_dir: str = "resources/data/charts"

    @classmethod
    def load(cls) -> WebSettings:
        """Nạp cấu hình kết hợp giữa file config.yaml và biến môi trường."""
        data = load_config_yaml_data()

        # Parse port
        port = int(
            os.environ.get("PORT")
            or os.environ.get("WEB_PORT")
            or os.environ.get("API_PORT")
            or data.get("app_port")
            or data.get("api_port")
            or 8000
        )

        # Parse host
        host = (
            os.environ.get("HOST")
            or os.environ.get("API_HOST")
            or data.get("app_host")
            or data.get("api_host")
            or "0.0.0.0"
        )

        # Parse AI microservice URL
        ai_base_url = (
            os.environ.get("AI_BASE_URL")
            or data.get("app_ai_base_url")
            or data.get("ai_base_url")
            or "http://127.0.0.1:8001"
        ).rstrip("/")

        # Parse Database URL
        database_url = os.environ.get("DATABASE_URL") or data.get("database_url")

        # Parse CORS
        cors_raw = os.environ.get("CORS_ORIGINS") or data.get("cors_origins") or "*"
        if isinstance(cors_raw, str):
            cors_origins = [o.strip() for o in cors_raw.split(",") if o.strip()]
        elif isinstance(cors_raw, list):
            cors_origins = [str(o) for o in cors_raw]
        else:
            cors_origins = ["*"]

        # Parse Charts Dir
        charts_dir = os.environ.get("CHARTS_DIR") or data.get("charts_dir") or "resources/data/charts"

        return cls(
            host=host,
            port=port,
            ai_base_url=ai_base_url,
            database_url=database_url,
            cors_origins=cors_origins,
            log_level=os.environ.get("LOG_LEVEL", "INFO"),
            charts_dir=charts_dir,
        )


# Singleton settings instance
web_settings = WebSettings.load()
settings = web_settings
