"""AI Backend specific settings loaded from config.yaml and environment variables."""

from __future__ import annotations

import os
from typing import Any

from common.base.base_model import CustomBaseModel
from common.settings.config import load_config_yaml_data


class AiSettings(CustomBaseModel):
    """Cấu hình microservice AI Backend (Cổng 8001)."""

    app_name: str = "VN Stock Swarm AI Microservice"
    version: str = "1.0.0"
    host: str = "0.0.0.0"
    port: int = 8001

    # Qdrant Vector Store
    qdrant_url: str | None = None
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_api_key: str | None = None
    qdrant_collection: str = "stock_concepts"

    # Redis Cache & Memory
    redis_url: str = "redis://localhost:6379/0"
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str | None = None

    # LLM Settings & Keys
    openai_api_key: str | None = None
    openai_base_url: str | None = None
    llm_backend: str = "mock"
    llm_model: str = "gpt-4o-mini"
    llm_temperature: float = 0.2
    llm_timeout: float = 30.0

    # Fallback and Safety
    price_fallback_on_error: bool = True
    input_guardrails_enabled: bool = True
    output_guardrails_enabled: bool = True
    exact_cache_enabled: bool = True
    semantic_cache_enabled: bool = True

    # Directories and Logging
    sqlite_path: str = "resources/data/portfolio_watch.db"
    charts_dir: str = "resources/data/charts"
    log_level: str = "INFO"
    cors_origins: list[str] = ["*"]

    @classmethod
    def load(cls) -> AiSettings:
        """Nạp cấu hình kết hợp giữa file config.yaml và biến môi trường."""
        data = load_config_yaml_data()

        # Parse port (AI backend mặc định 8001)
        port = int(
            os.environ.get("AI_PORT")
            or os.environ.get("AI_API_PORT")
            or os.environ.get("PORT")
            or data.get("ai_api_port")
            or data.get("ai_port")
            or 8001
        )

        # Parse host
        host = (
            os.environ.get("AI_HOST")
            or os.environ.get("AI_API_HOST")
            or os.environ.get("HOST")
            or data.get("ai_api_host")
            or data.get("ai_host")
            or "0.0.0.0"
        )

        # Parse Qdrant
        qdrant_url = os.environ.get("QDRANT_URL") or data.get("qdrant_url")
        qdrant_host = os.environ.get("QDRANT_HOST") or data.get("qdrant_host") or "localhost"
        qdrant_port = int(os.environ.get("QDRANT_PORT") or data.get("qdrant_port") or 6333)
        qdrant_api_key = os.environ.get("QDRANT_API_KEY") or data.get("qdrant_api_key")
        qdrant_collection = (
            os.environ.get("QDRANT_COLLECTION")
            or data.get("qdrant_collection")
            or "stock_concepts"
        )

        # Parse Redis
        redis_url = os.environ.get("REDIS_URL") or data.get("redis_url") or "redis://localhost:6379/0"
        redis_host = os.environ.get("REDIS_HOST") or data.get("redis_host") or "localhost"
        redis_port = int(os.environ.get("REDIS_PORT") or data.get("redis_port") or 6379)
        redis_password = os.environ.get("REDIS_PASSWORD") or data.get("redis_password")

        # Parse LLM
        openai_api_key = os.environ.get("OPENAI_API_KEY") or data.get("openai_api_key")
        openai_base_url = os.environ.get("OPENAI_BASE_URL") or data.get("openai_base_url")
        llm_backend = os.environ.get("LLM_BACKEND") or data.get("llm_backend") or "mock"
        llm_model = os.environ.get("LLM_MODEL") or data.get("llm_model") or "gpt-4o-mini"

        # Fallback & Toggles
        if "PRICE_FALLBACK_ON_ERROR" in os.environ:
            price_fallback = os.environ["PRICE_FALLBACK_ON_ERROR"].strip().lower() in ("true", "1", "yes")
        else:
            price_fallback = bool(data.get("price_fallback_on_error", True))

        # Charts Dir
        charts_dir = os.environ.get("CHARTS_DIR") or data.get("charts_dir") or "resources/data/charts"

        # CORS
        cors_raw = os.environ.get("CORS_ORIGINS") or data.get("cors_origins") or "*"
        if isinstance(cors_raw, str):
            cors_origins = [o.strip() for o in cors_raw.split(",") if o.strip()]
        elif isinstance(cors_raw, list):
            cors_origins = [str(o) for o in cors_raw]
        else:
            cors_origins = ["*"]

        # SQLite Path
        sqlite_path = (
            os.environ.get("SQLITE_PATH")
            or os.environ.get("BACKEND_SQLITE_PATH")
            or data.get("sqlite_path")
            or "resources/data/portfolio_watch.db"
        )

        return cls(
            host=host,
            port=port,
            qdrant_url=qdrant_url,
            qdrant_host=qdrant_host,
            qdrant_port=qdrant_port,
            qdrant_api_key=qdrant_api_key,
            qdrant_collection=qdrant_collection,
            redis_url=redis_url,
            redis_host=redis_host,
            redis_port=redis_port,
            redis_password=redis_password,
            openai_api_key=openai_api_key,
            openai_base_url=openai_base_url,
            llm_backend=llm_backend,
            llm_model=llm_model,
            price_fallback_on_error=price_fallback,
            sqlite_path=sqlite_path,
            charts_dir=charts_dir,
            cors_origins=cors_origins,
            log_level=os.environ.get("LOG_LEVEL", "INFO"),
        )


# Singleton instance
ai_settings = AiSettings.load()
