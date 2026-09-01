"""Cấu hình — đọc từ biến môi trường / file .env. Điểm DUY NHẤT đọc secrets."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    llm_model: str = Field(default="gpt-4o-mini", alias="LLM_MODEL")
    llm_base_url: str = Field(default="", alias="LLM_BASE_URL")
    llm_temperature: float = Field(default=0.2, alias="LLM_TEMPERATURE")

    guardrails_min_answer_len: int = Field(default=5, alias="GUARDRAILS_MIN_ANSWER_LEN")
    guardrails_max_answer_len: int = Field(default=2000, alias="GUARDRAILS_MAX_ANSWER_LEN")

    app_name: str = Field(default="agent_stat", alias="APP_NAME")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
