"""Tool HITL team scan — side-effect watchlist; `interrupt_before=["scan_tools"]` chờ resume_graph.

Cảnh báo soạn ở ``synthesis_node`` trả trong ``ScanSymbolResult.alert`` (không gửi qua tool).
"""

from __future__ import annotations

import json

from langchain_core.tools import tool
from langgraph.runtime import get_runtime

from common.domain.entities import WatchlistItem


@tool
def update_watchlist(
    user_id: str,
    symbol: str,
    threshold_pct: float,
    related_symbols: list[str] | None = None,
) -> str:
    """Áp ngưỡng cảnh báo đề xuất cho mã và thêm các mã liên quan (chưa có) vào watchlist."""
    store = get_runtime().context["watchlist_store"]
    sym = symbol.strip().upper()
    store.upsert(WatchlistItem(symbol=sym, threshold_pct=threshold_pct, user_id=user_id))
    updated = [sym]
    for rel in related_symbols or []:
        rel_sym = rel.strip().upper()
        if rel_sym and rel_sym != sym and store.get(user_id, rel_sym) is None:
            store.upsert(WatchlistItem(symbol=rel_sym, threshold_pct=threshold_pct, user_id=user_id))
            updated.append(rel_sym)
    return json.dumps({"updated": updated, "threshold_pct": threshold_pct}, ensure_ascii=False)


SCAN_ACTION_TOOLS = [update_watchlist]
