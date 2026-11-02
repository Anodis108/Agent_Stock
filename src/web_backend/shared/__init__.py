"""Shared package for Web Backend."""

from web_backend.shared.exceptions import (
    AiServiceUnavailableException,
    HoldingNotFoundException,
    SessionNotFoundException,
    ValidationException,
    WebBackendException,
    WebDatabaseException,
)
from web_backend.shared.settings import WebSettings, web_settings

__all__ = [
    "WebSettings",
    "web_settings",
    "WebBackendException",
    "WebDatabaseException",
    "SessionNotFoundException",
    "HoldingNotFoundException",
    "ValidationException",
    "AiServiceUnavailableException",
]
