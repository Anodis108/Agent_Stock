"""Backend package initialization.

Cung cấp 2 entrypoint độc lập:
- Web Backend: backend.main:app (cổng 8000)
- AI Backend: backend.ai_main:app (cổng 8001)

Đồng thời tích hợp meta path finder để tương thích ngược với các import cũ.
"""

from __future__ import annotations

import importlib
import importlib.util
import sys
import types
from typing import Any


class _AliasModule(types.ModuleType):
    """Proxy module chuyển tiếp thuộc tính sang target_mod mà không làm hỏng metadata của target."""

    def __init__(self, name: str, target: Any) -> None:
        super().__init__(name)
        object.__setattr__(self, "_target_module", target)

    def __getattr__(self, name: str) -> Any:
        target = object.__getattribute__(self, "_target_module")
        return getattr(target, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name in (
            "_target_module",
            "__name__",
            "__doc__",
            "__package__",
            "__loader__",
            "__spec__",
            "__path__",
            "__file__",
        ):
            super().__setattr__(name, value)
        else:
            setattr(object.__getattribute__(self, "_target_module"), name, value)


class _AliasLoader:
    """Loader trả về proxy _AliasModule bao bọc target_mod thay vì nạp lại module mới."""

    def __init__(self, target_mod: Any) -> None:
        self.target_mod = target_mod

    def create_module(self, spec: Any) -> Any:
        return _AliasModule(spec.name, self.target_mod)

    def exec_module(self, module: Any) -> None:
        module.__dict__.update(self.target_mod.__dict__)


_COMPAT_MODULE_MAP = {
    "backend.transport": "backend.shared.transport",
    "backend.charts": "backend.shared.charts",
    "backend.settings": "backend.shared.settings",
    "backend.logging": "backend.shared.logging",
    "backend.store": "backend.infra.storage.store",
    "backend.deps": "backend.shared.deps",
    "backend.validation": "backend.api.helpers.validation",
    "backend.cors_util": "backend.api.middleware.cors",
    "backend.steps": "backend.eval.steps",
    "backend.qdrant": "backend.infra.storage.long_term_memory",
    "backend.scan_symbol": "backend.application.scan_symbol",
    "backend.answer_question": "backend.application.answer_question",
    "backend.ai_client": "backend.infra.llm.client",
    "backend.app": "backend.ai_main",
    "backend.routes": "backend.api.routers.ai.v1",
    "backend.routes.chat": "backend.api.routers.web.chat",
    "backend.routes.watchlist": "backend.api.routers.web.watchlist",
    "backend.api.routers.chat": "backend.api.routers.web.chat",
    "backend.api.routers.hitl": "backend.api.routers.web.hitl",
    "backend.api.routers.market": "backend.api.routers.web.market",
    "backend.api.routers.portfolio": "backend.api.routers.web.portfolio",
    "backend.api.routers.scan": "backend.api.routers.web.scan",
    "backend.api.routers.sessions": "backend.api.routers.web.sessions",
    "backend.api.routers.watchlist": "backend.api.routers.web.watchlist",
    "backend.api.routers.approvals": "backend.api.routers.web.approvals",
    "backend.api.routers.v1": "backend.api.routers.ai.v1",
    "backend.api.main": "backend.main",
}


_COMPAT_PREFIX_MAP = {
    "backend.database": "backend.infra.database",
    "backend.retrieval": "backend.infra.retrieval",
    "backend.services": "backend.application.services",
    "backend.agents": "backend.application.agents",
    "backend.graph": "backend.application.graph",
    "backend.eval": "backend.application.eval",
}


class _CompatFinder:
    """Meta path finder redirect các import module cũ sang vị trí kiến trúc mới theo chuẩn Clean Architecture."""

    @classmethod
    def find_spec(cls, fullname: str, path: Any = None, target: Any = None) -> Any:
        target_name = _COMPAT_MODULE_MAP.get(fullname)
        if not target_name:
            for old_p, new_p in _COMPAT_PREFIX_MAP.items():
                if fullname == old_p or fullname.startswith(old_p + "."):
                    target_name = new_p + fullname[len(old_p):]
                    break

        if target_name:
            try:
                if target_name in sys.modules:
                    target_mod = sys.modules[target_name]
                else:
                    target_mod = importlib.import_module(target_name)

                sys.modules[fullname] = target_mod
                parts = fullname.split(".")
                if len(parts) > 1:
                    parent = ".".join(parts[:-1])
                    if parent in sys.modules:
                        setattr(sys.modules[parent], parts[-1], target_mod)
                is_pkg = hasattr(target_mod, "__path__")
                return importlib.util.spec_from_loader(
                    fullname,
                    _AliasLoader(target_mod),
                    is_package=is_pkg,
                )

            except Exception:
                return None
        return None



if not any(
    isinstance(f, _CompatFinder)
    or getattr(f, "__name__", "") == "_CompatFinder"
    for f in sys.meta_path
):
    sys.meta_path.insert(0, _CompatFinder)


