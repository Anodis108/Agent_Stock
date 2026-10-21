"""Cấu hình dùng chung — CHỈ đọc từ biến môi trường.

Mọi trường khởi tạo là None; giá trị đến từ biến môi trường cùng tên (viết hoa), ví dụ
`llm_model` ← `LLM_MODEL`. Chạy local: `load_dotenv` nạp file `.env` thành biến môi trường
(không ghi đè biến đã có). Danh sách đầy đủ biến: `.env.example`.
"""

from __future__ import annotations

from dotenv import find_dotenv, load_dotenv
from pydantic import field_validator
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict

load_dotenv(find_dotenv(".env"), override=False)


class Settings(BaseSettings):
    """Cấu hình tập trung, nguồn duy nhất: biến môi trường."""

    model_config = SettingsConfigDict(extra="ignore")

    # 1. LLM backend & cascade
    llm_backend: str | None = None
    llm_base_url: str | None = None
    openai_api_keys: str | None = None
    llm_model: str | None = None
    llm_temperature: float | None = None
    llm_max_completion_tokens: int | None = None
    llm_top_p: float | None = None
    llm_max_retries: int | None = None
    llm_max_concurrency: int | None = None
    llm_model_cascade: str | None = None
    llm_fallback_backends: str | None = None

    # 2. A/B prompt testing
    prompt_ab_enabled: bool | None = None
    prompt_ab_version_a: str | None = None
    prompt_ab_version_b: str | None = None
    prompt_ab_split_pct: int | None = None

    # 3. Eval & Testing
    eval_cache_enabled: bool | None = None
    eval_cache_dir: str | None = None
    golden_dataset_path: str | None = None
    replay_faq_path: str | None = None
    confidence_auto_send_min: float | None = None

    # 4. Secret Manager
    use_secret_manager: bool | None = None

    # 5. Cost budget & Governance
    cost_daily_limit_usd: float | None = None
    cost_alert_threshold_usd: float | None = None

    # 6. App & Server
    app_name: str | None = None
    log_level: str | None = None
    api_host: str | None = None
    api_port: int | None = None
    cors_origins: list[str] | None = None
    frontend_origin: str | None = None
    backend_base_url: str | None = None
    app_host_port: int | None = None

    # 7. Split deploy
    ai_base_url: str | None = None
    ai_api_host: str | None = None
    ai_api_port: int | None = None
    ai_transport: str | None = None
    ai_http_timeout: int | None = None

    # 8. Watchlist & Alerts
    default_watchlist: str | None = None
    default_alert_threshold_pct: float | None = None
    scan_interval_minutes: int | None = None

    # 9. Data sources & Storage
    price_source: str | None = None
    news_source: str | None = None
    price_fallback_on_error: bool | None = None
    sqlite_path: str | None = None
    backend_sqlite_path: str | None = None
    chart_dir: str | None = None
    chart_backend: str | None = None
    minio_endpoint: str | None = None
    minio_bucket: str | None = None
    minio_secure: bool | None = None
    minio_access_key: str | None = None
    minio_secret_key: str | None = None
    postgres_host: str | None = None
    postgres_port: int | None = None
    postgres_db: str | None = None
    database_url: str | None = None
    concept_collection: str | None = None

    @field_validator("chart_backend")
    @classmethod
    def chart_backend_is_local_or_minio(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        if normalized not in {"local", "minio"}:
            raise ValueError("CHART_BACKEND phải là local hoặc minio")
        return normalized

    # 10. 2-Tier Caching System
    cache_backend: str | None = None
    cache_exact_enabled: bool | None = None
    cache_semantic_enabled: bool | None = None
    cache_semantic_threshold: float | None = None
    cache_ttl_seconds: int | None = None
    redis_url: str | None = None

    @field_validator("cache_backend")
    @classmethod
    def cache_backend_is_memory_or_redis(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        if normalized not in {"memory", "redis"}:
            raise ValueError("CACHE_BACKEND phải là memory hoặc redis")
        return normalized

    # 11. Memory short-term & freshness
    memory_short_term_window: int | None = None
    memory_short_term_ttl_minutes: int | None = None

    # 12. Memory long-term & Qdrant
    qdrant_url: str | None = None
    qdrant_host: str | None = None
    qdrant_port: int | None = None
    qdrant_api_key: str | None = None
    qdrant_collection: str | None = None
    embedding_model: str | None = None
    embedding_dim: int | None = None

    # 13. Monitoring & Tracing
    monitoring_enabled: bool | None = None
    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None
    langfuse_host: str | None = None
    langfuse_sample_rate: float | None = None

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        # Chỉ biến môi trường (init_settings để test/khởi tạo tay truyền giá trị trực tiếp)
        return init_settings, env_settings

    @property
    def api_keys(self) -> list[str]:
        return [k.strip() for k in (self.openai_api_keys or "").split(",") if k.strip()]

    @property
    def default_symbols(self) -> list[str]:
        return [s.strip().upper() for s in (self.default_watchlist or "").split(",") if s.strip()]

    @property
    def model_cascade_list(self) -> list[str]:
        return [m.strip() for m in (self.llm_model_cascade or "").split(",") if m.strip()]

    @property
    def fallback_backends_list(self) -> list[str]:
        return [b.strip().lower() for b in (self.llm_fallback_backends or "").split(",") if b.strip()]


settings = Settings()

if settings.use_secret_manager:
    from common.settings.secrets import apply_runtime_secrets

    apply_runtime_secrets(settings)


def load_config() -> Settings:
    """Nạp lại cấu hình từ biến môi trường hiện tại."""
    return Settings()
