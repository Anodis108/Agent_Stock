from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import find_dotenv, load_dotenv
from pydantic import field_validator
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict

# Nạp biến môi trường từ file .env (chỉ nạp các biến chưa có trong process environment)
load_dotenv(find_dotenv(".env"), override=False)


def get_config_yaml_path() -> Path:
    """Xác định đường dẫn tệp cấu hình config.yaml duy nhất của ứng dụng."""
    if os.environ.get("CONFIG_YAML_PATH"):
        return Path(os.environ["CONFIG_YAML_PATH"])

    # src/common/settings/config.py -> resources/configs/config.yaml
    project_root = Path(__file__).resolve().parent.parent.parent.parent
    candidate = project_root / "resources" / "configs" / "config.yaml"
    if candidate.exists():
        return candidate

    cwd_candidate = Path.cwd() / "resources" / "configs" / "config.yaml"
    if cwd_candidate.exists():
        return cwd_candidate

    return candidate


def load_config_yaml_data(yaml_path: Path | None = None) -> dict[str, Any]:
    """Đọc và làm phẳng cấu trúc lồng nhau trong file config.yaml thành các trường phẳng."""
    if yaml_path is None:
        yaml_path = get_config_yaml_path()

    if not yaml_path.exists():
        return {}

    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
    except Exception:
        return {}

    flat: dict[str, Any] = {}
    for section, content in raw.items():
        if isinstance(content, dict):
            for k, v in content.items():
                flat[f"{section}_{k}"] = v
                flat[k] = v
        else:
            flat[section] = content

    # Bảng ánh xạ bí danh (Aliases) tương thích hoàn toàn với Settings
    alias_map: dict[str, str] = {
        "app_name": "app_name",
        "app_host": "api_host",
        "app_port": "api_port",
        "app_log_level": "log_level",
        "app_cors_origins": "cors_origins",
        "app_frontend_origin": "frontend_origin",
        "app_backend_base_url": "backend_base_url",
        "app_ai_base_url": "ai_base_url",
        "app_ai_transport": "ai_transport",
        "app_ai_http_timeout": "ai_http_timeout",
        "app_ai_api_host": "ai_api_host",
        "app_ai_api_port": "ai_api_port",
        "app_app_host_port": "app_host_port",
        "llm_backend": "llm_backend",
        "llm_base_url": "llm_base_url",
        "llm_model": "llm_model",
        "llm_temperature": "llm_temperature",
        "llm_max_completion_tokens": "llm_max_completion_tokens",
        "llm_top_p": "llm_top_p",
        "llm_max_retries": "llm_max_retries",
        "llm_max_concurrency": "llm_max_concurrency",
        "llm_model_cascade": "llm_model_cascade",
        "llm_fallback_backends": "llm_fallback_backends",
        "cache_backend": "cache_backend",
        "cache_exact_enabled": "cache_exact_enabled",
        "cache_semantic_enabled": "cache_semantic_enabled",
        "cache_semantic_threshold": "cache_semantic_threshold",
        "cache_ttl_seconds": "cache_ttl_seconds",
        "memory_short_term_window": "memory_short_term_window",
        "memory_short_term_ttl_minutes": "memory_short_term_ttl_minutes",
        "memory_embedding_model": "embedding_model",
        "memory_embedding_dim": "embedding_dim",
        "memory_qdrant_collection": "qdrant_collection",
        "storage_sqlite_path": "sqlite_path",
        "storage_backend_sqlite_path": "backend_sqlite_path",
        "storage_chart_dir": "chart_dir",
        "storage_chart_backend": "chart_backend",
        "storage_minio_endpoint": "minio_endpoint",
        "storage_minio_bucket": "minio_bucket",
        "storage_minio_secure": "minio_secure",
        "storage_postgres_host": "postgres_host",
        "storage_postgres_port": "postgres_port",
        "storage_postgres_db": "postgres_db",
        "storage_concept_collection": "concept_collection",
        "market_data_price_source": "price_source",
        "market_data_news_source": "news_source",
        "market_data_fallback_on_error": "price_fallback_on_error",
        "market_data_default_watchlist": "default_watchlist",
        "market_data_default_alert_threshold_pct": "default_alert_threshold_pct",
        "market_data_scan_interval_minutes": "scan_interval_minutes",
        "eval_golden_dataset_path": "golden_dataset_path",
        "eval_replay_faq_path": "replay_faq_path",
        "eval_eval_cache_enabled": "eval_cache_enabled",
        "eval_eval_cache_dir": "eval_cache_dir",
        "eval_cost_daily_limit_usd": "cost_daily_limit_usd",
        "eval_cost_alert_threshold_usd": "cost_alert_threshold_usd",
        "eval_confidence_auto_send_min": "confidence_auto_send_min",
        "eval_prompt_ab_enabled": "prompt_ab_enabled",
        "eval_prompt_ab_version_a": "prompt_ab_version_a",
        "eval_prompt_ab_version_b": "prompt_ab_version_b",
        "eval_prompt_ab_split_pct": "prompt_ab_split_pct",
        "secrets_use_secret_manager": "use_secret_manager",
        "monitoring_enabled": "monitoring_enabled",
        "monitoring_sample_rate": "langfuse_sample_rate",
    }
    for src_k, target_k in alias_map.items():
        if src_k in flat:
            flat[target_k] = flat[src_k]

    return flat


class YamlConfigSettingsSource(PydanticBaseSettingsSource):
    """Nguồn nạp cấu hình tùy biến từ config.yaml cho Pydantic Settings."""

    def __init__(self, settings_cls: type[BaseSettings], yaml_path: Path | None = None) -> None:
        super().__init__(settings_cls)
        self.yaml_path = yaml_path
        self._yaml_data = load_config_yaml_data(yaml_path)

    def get_field_value(self, field: Any, field_name: str) -> tuple[Any, str, bool]:
        return None, field_name, False

    def __call__(self) -> dict[str, Any]:
        return self._yaml_data


class Settings(BaseSettings):
    """Quản trị cấu hình tập trung kết hợp config.yaml (runtime) và .env (secrets)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # 1. LLM backend & cascade
    llm_backend: str = "openai"
    llm_base_url: str | None = None
    openai_api_keys: str = "not-needed"
    llm_model: str = "gpt-4o-mini"
    llm_temperature: float = 0.2
    llm_max_completion_tokens: int = 800
    llm_top_p: float = 1.0
    llm_max_retries: int = 3
    llm_max_concurrency: int = 5
    llm_model_cascade: str = ""
    llm_fallback_backends: str = ""

    # 2. A/B prompt testing
    prompt_ab_enabled: bool = False
    prompt_ab_version_a: str = "production"
    prompt_ab_version_b: str = "v2"
    prompt_ab_split_pct: int = 50

    # 3. Eval & Testing
    eval_cache_enabled: bool = True
    eval_cache_dir: str = ".eval_cache"
    golden_dataset_path: str = "./resources/eval/golden_dataset.yaml"
    replay_faq_path: str = "./resources/eval/replay_faq.yaml"
    confidence_auto_send_min: float = 0.8

    # 4. Secret Manager. Tắt thì secret lấy từ .env.
    use_secret_manager: bool = False

    # 5. Cost budget & Governance
    cost_daily_limit_usd: float = 0.0
    cost_alert_threshold_usd: float = 1.0

    # 6. App & Server
    app_name: str = "Portfolio Watch & Chat Agent"
    log_level: str = "INFO"
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    cors_origins: list[str] = ["*"]
    frontend_origin: str = "http://127.0.0.1:5173"
    backend_base_url: str = "http://127.0.0.1:8000"
    app_host_port: int = 8088

    # 7. Split deploy
    ai_base_url: str = "http://127.0.0.1:8001"
    ai_api_host: str = "127.0.0.1"
    ai_api_port: int = 8001
    ai_transport: str = "inprocess"
    ai_http_timeout: int = 60

    # 8. Watchlist & Alerts
    default_watchlist: str = "FPT,VNM,HPG"
    default_alert_threshold_pct: float = 3.0
    scan_interval_minutes: int = 60

    # 9. Data sources & Storage
    price_source: str = "vnstock"
    news_source: str = "cafef"
    price_fallback_on_error: bool = True
    sqlite_path: str = "./resources/data/portfolio_watch.db"
    backend_sqlite_path: str = "./resources/data/backend_store.db"
    chart_dir: str = "./resources/data/charts"
    chart_backend: str = "minio"
    minio_endpoint: str = "localhost:9000"
    minio_bucket: str = "charts"
    minio_secure: bool = False
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "portfolio_watch"
    database_url: str = ""
    concept_collection: str = "stock_concepts"

    @field_validator("chart_backend")
    @classmethod
    def chart_backend_is_local_or_minio(cls, value: str) -> str:
        normalized = (value or "").strip().lower()
        if normalized not in {"local", "minio"}:
            raise ValueError("storage.chart_backend phải là local hoặc minio")
        return normalized

    # 10. 2-Tier Caching System
    cache_backend: str = "memory"
    cache_exact_enabled: bool = True
    cache_semantic_enabled: bool = True
    cache_semantic_threshold: float = 0.93
    cache_ttl_seconds: int = 86400

    @field_validator("cache_backend")
    @classmethod
    def cache_backend_is_memory_or_redis(cls, value: str) -> str:
        normalized = (value or "").strip().lower()
        if normalized not in {"memory", "redis"}:
            raise ValueError("cache.backend phải là memory hoặc redis")
        return normalized

    # 11. Memory short-term & freshness
    memory_short_term_window: int = 20
    memory_short_term_ttl_minutes: int = 60

    # 12. Memory long-term & Qdrant
    qdrant_url: str | None = None
    qdrant_api_key: str | None = None
    qdrant_collection: str = "portfolio_watch_memory"
    embedding_model: str = "text-embedding-3-small"
    embedding_dim: int = 1536

    # 13. Monitoring & Tracing
    monitoring_enabled: bool = False
    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None
    langfuse_host: str = "https://cloud.langfuse.com"
    langfuse_sample_rate: float = 1.0

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            YamlConfigSettingsSource(settings_cls),
            file_secret_settings,
        )

    @property
    def api_keys(self) -> list[str]:
        return [k.strip() for k in self.openai_api_keys.split(",") if k.strip()]

    @property
    def default_symbols(self) -> list[str]:
        return [s.strip().upper() for s in self.default_watchlist.split(",") if s.strip()]

    @property
    def model_cascade_list(self) -> list[str]:
        if not self.llm_model_cascade.strip():
            return []
        return [m.strip() for m in self.llm_model_cascade.split(",") if m.strip()]

    @property
    def fallback_backends_list(self) -> list[str]:
        if not self.llm_fallback_backends.strip():
            return []
        return [b.strip().lower() for b in self.llm_fallback_backends.split(",") if b.strip()]


settings = Settings()

if settings.use_secret_manager:
    from common.settings.secrets import apply_runtime_secrets

    apply_runtime_secrets(settings)


def load_config() -> Settings:
    """Nạp cấu hình ứng dụng."""
    return Settings()
