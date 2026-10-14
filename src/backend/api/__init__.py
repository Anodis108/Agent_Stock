"""FastAPI layer — routers, middleware, deps, app entrypoint."""

from typing import Any


def __getattr__(name: str) -> Any:
    if name == "app":
        from backend.main import app

        return app
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["app"]

