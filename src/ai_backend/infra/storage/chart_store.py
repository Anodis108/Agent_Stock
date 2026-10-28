"""MinIO / Local Object Store for Charts.

Delegates to unified common.storage while preserving local chart directory support.
"""
from __future__ import annotations


import ai_backend.shared.charts as backend_charts
from common.storage import (
    ChartObjectStore,
    get_chart_store,
    reset_chart_store,
    safe_png_name,
)


def read_chart_png(name: str) -> bytes | None:
    safe_name = safe_png_name(name)
    if not safe_name:
        return None
    store = get_chart_store()
    if store is not None:
        data = store.get(safe_name)
        if data is not None:
            return data
    path = backend_charts.get_charts_dir() / safe_name
    if path.is_file():
        return path.read_bytes()
    return None


__all__ = [
    "ChartObjectStore",
    "get_chart_store",
    "read_chart_png",
    "reset_chart_store",
    "safe_png_name",
]
