"""Tool worker db_agent — đọc danh mục nắm giữ + watchlist của người dùng (artifact {"db_results": DBAgentResult}).
"""

from __future__ import annotations

import json
import logging
from typing import Annotated, Any

from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState
from langgraph.runtime import get_runtime

from ai_backend.domain.agents.scan.db_agent.state import DBAgentResult

_logger = logging.getLogger(__name__)


def read_holdings(user_id: str) -> list[dict[str, Any]]:
    from web_backend.infra.database.connection import get_connection

    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT id, user_id, symbol, quantity, avg_buy_price, purchase_date "
            "FROM portfolio_holdings WHERE user_id = ? ORDER BY symbol",
            (user_id,),
        ).fetchall()
        return [
            {
                "id": str(r["id"]),
                "user_id": str(r["user_id"]),
                "symbol": str(r["symbol"]).strip().upper(),
                "quantity": float(r["quantity"]),
                "avg_buy_price": float(r["avg_buy_price"]),
                "purchase_date": r["purchase_date"],
            }
            for r in rows
        ]
    finally:
        conn.close()


def read_watchlist(user_id: str) -> list[dict[str, Any]]:
    store = get_runtime().context["watchlist_store"]
    if store is not None and hasattr(store, "list_items"):
        return [{"user_id": i.user_id, "symbol": i.symbol, "threshold_pct": i.threshold_pct} for i in store.list_items(user_id)]
    from web_backend.infra.database.connection import get_connection

    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT user_id, symbol, threshold_pct FROM watchlist WHERE user_id = ? ORDER BY symbol", (user_id,)
        ).fetchall()
        return [{"user_id": str(r["user_id"]), "symbol": str(r["symbol"]).upper(), "threshold_pct": float(r["threshold_pct"])} for r in rows]
    finally:
        conn.close()


def db_results_from_tool_artifacts(message_worker: list) -> DBAgentResult | None:
    """Lần gọi read_user_portfolio cuối → artifact {"db_results": DBAgentResult}; chưa gọi → None."""
    results = [
        a["db_results"]
        for m in message_worker
        if getattr(m, "type", None) == "tool"
        and (a := getattr(m, "artifact", None)) is not None
        and "db_results" in a
    ]
    return results[-1] if results else None


@tool(response_format="content_and_artifact")
def read_user_portfolio(user_id: Annotated[str, InjectedState("user_id")] = "default"):
    """Đọc danh mục nắm giữ (mã, số lượng, giá vốn) VÀ watchlist (mã, ngưỡng cảnh báo %) của người dùng hiện tại."""
    result = DBAgentResult(user_id=user_id or "default")
    try:
        result.holdings = read_holdings(result.user_id)
        result.watchlist = read_watchlist(result.user_id)
    except Exception as exc:  # noqa: BLE001
        _logger.warning("read_user_portfolio lỗi: %s", exc)
        result.error = f"lỗi đọc DB: {exc}"
    text = result.error or f"{len(result.holdings)} mã nắm giữ, {len(result.watchlist)} mã watchlist: " + json.dumps(
        {"holdings": result.holdings, "watchlist": result.watchlist}, ensure_ascii=False
    )
    return text, {"db_results": result}


PORTFOLIO_TOOLS = [read_user_portfolio]

