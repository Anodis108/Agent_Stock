"""Backend package initialization.

Cung cấp 2 entrypoint độc lập:
- Web Backend: backend.main:app (cổng 8000)
- AI Backend: backend.ai_main:app (cổng 8001)

Đồng thời tích hợp meta path finder để tương thích ngược với các import cũ.
"""

from __future__ import annotations

import importlib
import sys
from typing import Any

_COMPAT_MODULE_MAP = {
    "backend.transport": "backend.shared.transport",
    "backend.charts": "backend.shared.charts",
    "backend.settings": "backend.shared.settings",
    "backend.logging": "backend.shared.logging",
    "backend.store": "backend.infra.storage.store",
    "backend.deps": "backend.api.deps",
    "backend.validation": "backend.api.helpers.validation",
    "backend.cors_util": "backend.api.middleware.cors",
    "backend.steps": "backend.eval.steps",
    "backend.qdrant": "backend.infra.storage.long_term_memory",
    "backend.scan_symbol": "backend.application.scan_symbol",
    "backend.answer_question": "backend.application.answer_question",
    "backend.ai_client": "backend.infra.llm.client",
    "backend.app": "backend.ai_main",
}


class _CompatFinder:
    """Meta path finder redirect các import module cũ sang vị trí kiến trúc mới."""

    @classmethod
    def find_spec(cls, fullname: str, path: Any = None, target: Any = None) -> Any:
        target_name = _COMPAT_MODULE_MAP.get(fullname)
        if target_name:
            target_mod = importlib.import_module(target_name)
            sys.modules[fullname] = target_mod
            return target_mod.__spec__
        return None


if not any(
    isinstance(f, _CompatFinder)
    or getattr(f, "__name__", "") == "_CompatFinder"
    for f in sys.meta_path
):
    sys.meta_path.insert(0, _CompatFinder)
