"""API Routers package.

Phân chia rõ ràng thành:
- web: Routers phục vụ ứng dụng Web (cổng 8000)
- ai: Routers phục vụ microservice AI Swarm (cổng 8001)
"""

from __future__ import annotations

import sys
from backend.api.routers import ai, web
from backend.api.routers.ai import v1
from backend.api.routers.web import (
    approvals,
    chat,
    hitl,
    market,
    portfolio,
    scan,
    sessions,
    watchlist,
)

# Populate sys.modules cho tương thích ngược hoàn toàn với các import phẳng cũ
_MODULES = {
    "backend.api.routers.approvals": approvals,
    "backend.api.routers.chat": chat,
    "backend.api.routers.hitl": hitl,
    "backend.api.routers.market": market,
    "backend.api.routers.portfolio": portfolio,
    "backend.api.routers.scan": scan,
    "backend.api.routers.sessions": sessions,
    "backend.api.routers.watchlist": watchlist,
    "backend.api.routers.v1": v1,
}

for _mod_name, _mod in _MODULES.items():
    sys.modules.setdefault(_mod_name, _mod)

__all__ = [
    "web",
    "ai",
    "approvals",
    "chat",
    "hitl",
    "market",
    "portfolio",
    "scan",
    "sessions",
    "watchlist",
    "v1",
]
