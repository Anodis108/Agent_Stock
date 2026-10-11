"""Backward compatibility redirect to backend.api.middleware.cors."""

from __future__ import annotations

from backend.api.middleware.cors import resolve_cors_origins

__all__ = ["resolve_cors_origins"]
