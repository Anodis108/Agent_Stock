"""Shared utilities and configurations for AI Backend."""

from __future__ import annotations

from ai_backend.shared.charts import apply_chart_style, get_charts_dir
from ai_backend.shared.exceptions import (
    AiBackendException,
    GuardrailViolation,
    LLMTimeoutException,
    ModelProviderException,
    PromptTemplateException,
    QdrantUnavailableException,
    RedisUnavailableException,
    ScanExecutionException,
)
from ai_backend.shared.settings import AiSettings, ai_settings

__all__ = [
    "AiSettings",
    "ai_settings",
    "AiBackendException",
    "GuardrailViolation",
    "LLMTimeoutException",
    "ModelProviderException",
    "PromptTemplateException",
    "QdrantUnavailableException",
    "RedisUnavailableException",
    "ScanExecutionException",
    "apply_chart_style",
    "get_charts_dir",
]
