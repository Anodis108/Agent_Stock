"""API middleware package."""

from backend.api.middleware.cors import resolve_cors_origins

__all__ = ["resolve_cors_origins"]
