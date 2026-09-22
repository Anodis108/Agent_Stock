from __future__ import annotations

from dotenv import find_dotenv, load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv(find_dotenv(".env"), override=False)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM backend: openai | ollama | vllm
    llm_backend: str = "openai"
    llm_base_url: str | None = None
    openai_api_keys: str = "not-needed"
    llm_model: str = "gpt-4o-mini"
    llm_temperature: float = 0.2
    llm_max_completion_tokens: int = 800
    llm_top_p: float = 1.0
    llm_max_retries: int = 5

    # App
    app_name: str = "Portfolio Watch & Chat Agent"
    log_level: str = "INFO"
    api_host: str = "127.0.0.1"
    api_port: int = 8000

    # Split deploy
    ai_base_url: str = "http://127.0.0.1:8001"
    backend_base_url: str = "http://127.0.0.1:8000"
    frontend_origin: str = "http://127.0.0.1:5173"
    app_host_port: int = 8000
    # AI process bind (Phase 3a)
    ai_api_host: str = "127.0.0.1"
    ai_api_port: int = 8001

    # Watchlist defaults (MVP — 1 demo user)
    default_watchlist: str = "FPT,VNM,HPG"
    default_alert_threshold_pct: float = 3.0

    # Data sources / storage
    price_source: str = "vnstock"
    news_source: str = "cafef"
    sqlite_path: str = "./data/portfolio_watch.db"

    # Cron (minutes)
    scan_interval_minutes: int = 60

    # Memory short-term & freshness (Phase 7)
    memory_short_term_window: int = 20
    memory_short_term_ttl_minutes: int = 60

    # Memory long-term & Qdrant (Phase 8)
    qdrant_url: str | None = None
    qdrant_api_key: str | None = None
    qdrant_collection: str = "portfolio_watch_memory"
    embedding_model: str = "text-embedding-3-small"
    embedding_dim: int = 1536

    # Confidence gate (chốt công thức cụ thể ở phase sau)
    confidence_auto_send_min: float = 0.8

    # Monitoring (optional)
    monitoring_enabled: bool = False
    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None
    langfuse_host: str = "https://cloud.langfuse.com"

    @property
    def api_keys(self) -> list[str]:
        return [k.strip() for k in self.openai_api_keys.split(",") if k.strip()]

    @property
    def default_symbols(self) -> list[str]:
        return [s.strip().upper() for s in self.default_watchlist.split(",") if s.strip()]


settings = Settings()
