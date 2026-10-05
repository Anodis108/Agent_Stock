"""PortfolioWatchAgent — Quản lý danh mục đầu tư (Holdings, P&L, NAV) và Danh sách theo dõi (Watchlist)."""

from __future__ import annotations

import logging
from typing import Any, Literal

from backend.agents.portfolio_watch_agent.schemas import PortfolioWatchAgentResult
from backend.database.connection import get_connection
from backend.database.repositories import (
    PortfolioHoldingRepository,
    UserSettingsRepository,
)
from backend.domain.entities import WatchlistItem
from backend.domain.ports import PriceSource, WatchlistStore
from backend.infra.monitoring.tracing import agent_step
from backend.infra.storage.watchlist_store import SqliteWatchlistStore
from backend.services.portfolio_service import PortfolioService
from backend.shared.settings import settings

_logger = logging.getLogger(__name__)


def format_portfolio_markdown(summary: Any, user_id: str) -> str:
    """Định dạng bản tóm tắt danh mục đầu tư chuẩn Markdown."""
    if not summary:
        return f"Hiện tại không tìm thấy thông tin danh mục của tài khoản `{user_id}`."

    items = getattr(summary, "items", []) or []
    total_nav = getattr(summary, "total_nav", 0.0)
    total_cost = getattr(summary, "total_cost", 0.0)
    total_pnl = getattr(summary, "total_unrealized_pnl", 0.0)
    total_pnl_pct = getattr(summary, "total_pnl_pct", 0.0)

    pnl_sign = "+" if total_pnl > 0 else ""
    pct_sign = "+" if total_pnl_pct > 0 else ""

    lines = [
        f"### 💼 Báo Cáo Hiệu Suất Danh Mục Đầu Tư (Tài khoản: `{user_id}`)\n",
        f"- **Tổng giá trị tài sản (NAV)**: **{total_nav:,.0f} VND**",
        f"- **Tổng vốn đầu tư**: **{total_cost:,.0f} VND**",
        f"- **Lãi/Lỗ tạm tính (P&L)**: **{pnl_sign}{total_pnl:,.0f} VND** ({pct_sign}{total_pnl_pct:.2f}%)\n",
    ]

    if not items:
        lines.append(
            "> ℹ️ **Danh mục hiện chưa có cổ phiếu nào.**\n"
            "> Bạn có thể thêm cổ phiếu vào danh mục để hệ thống tự động theo dõi thị giá và lãi/lỗ theo thời gian thực."
        )
    else:
        lines.append("| Mã CP | Khối lượng | Giá vốn (nghìn VNĐ) | Thị giá (nghìn VNĐ) | Lãi/Lỗ (VND) | Tỷ suất sinh lời |")
        lines.append("| :--- | :---: | :---: | :---: | :---: | :---: |")
        for item in items:
            cur_p = getattr(item, "current_price", None)
            cur_str = f"{cur_p:,.1f}" if cur_p is not None else "Đang cập nhật"
            i_pnl = getattr(item, "unrealized_pnl", 0.0)
            i_pct = getattr(item, "pnl_pct", 0.0)
            i_sign = "+" if i_pnl > 0 else ""
            i_pct_sign = "+" if i_pct > 0 else ""
            lines.append(
                f"| **{item.symbol}** | {item.quantity:,} | {item.cost_basis:,.1f} | {cur_str} | {i_sign}{i_pnl:,.0f} | {i_pct_sign}{i_pct:.2f}% |"
            )

    return "\n".join(lines)


def format_watchlist_markdown(items: list[WatchlistItem], user_id: str) -> str:
    """Định dạng danh sách theo dõi kèm ngưỡng cảnh báo chuẩn Markdown."""
    lines = [f"### 📋 Danh Sách Theo Dõi & Ngưỡng Cảnh Báo (Watchlist - `{user_id}`)\n"]
    if not items:
        lines.append(
            "> ℹ️ **Danh sách theo dõi của bạn hiện đang trống.**\n"
            "> Bạn có thể thêm các mã cổ phiếu quan tâm vào Watchlist và thiết lập ngưỡng cảnh báo biến động (ví dụ: ±3% hoặc ±5%) để nhận thông báo kịp thời."
        )
    else:
        lines.append("| STT | Mã cổ phiếu | Ngưỡng cảnh báo biến động | Trạng thái giám sát |")
        lines.append("| :---: | :--- | :---: | :---: |")
        for idx, it in enumerate(items, 1):
            lines.append(f"| {idx} | **{it.symbol}** | ±{it.threshold_pct:.1f}% | Đang theo dõi |")
        lines.append(f"\n*Tổng cộng: **{len(items)}** mã trong danh sách theo dõi.*")

    return "\n".join(lines)


def run_portfolio_watch_agent(
    user_id: str = "default",
    intent: Literal["portfolio", "watchlist", "all"] = "all",
    *,
    price_source: PriceSource | None = None,
    watchlist_store: WatchlistStore | None = None,
    turn: str = "",
) -> PortfolioWatchAgentResult:
    """Thực thi tác vụ truy vấn danh mục hoặc watchlist cho người dùng."""
    eff_user_id = (user_id or "default").strip() or "default"
    summary = None
    watchlist_items: list[WatchlistItem] = []
    err: str | None = None

    with agent_step(turn, "portfolio_watch_agent", "fetch_portfolio_and_watchlist", input={"user_id": eff_user_id, "intent": intent}) as box:
        try:
            # 1. Truy vấn Danh mục đầu tư (Holdings, NAV, P&L)
            if intent in ("portfolio", "all"):
                try:
                    conn = get_connection()
                    try:
                        h_repo = PortfolioHoldingRepository(conn)
                        u_repo = UserSettingsRepository(conn)
                        ps = PortfolioService(h_repo, u_repo, price_source)
                        summary = ps.get_portfolio_summary(eff_user_id)
                    finally:
                        conn.close()
                except Exception as exc:
                    _logger.warning("Lỗi truy vấn danh mục trong PortfolioWatchAgent: %s", exc)
                    err = f"Lỗi truy vấn danh mục: {exc}"

            # 2. Truy vấn Danh sách theo dõi (Watchlist)
            if intent in ("watchlist", "all"):
                try:
                    store = watchlist_store
                    if store is None:
                        from backend.store import default_db_path
                        db_p = default_db_path()
                        store = SqliteWatchlistStore(db_p)
                        watchlist_items = store.list_items(eff_user_id)
                        if not watchlist_items and settings.sqlite_path != db_p:
                            fallback_store = SqliteWatchlistStore(settings.sqlite_path)
                            watchlist_items = fallback_store.list_items(eff_user_id)
                    else:
                        watchlist_items = store.list_items(eff_user_id)
                except Exception as exc:
                    _logger.warning("Lỗi truy vấn watchlist trong PortfolioWatchAgent: %s", exc)
                    if not err:
                        err = f"Lỗi truy vấn watchlist: {exc}"

            # 3. Kết hợp định dạng Markdown
            parts: list[str] = []
            if intent in ("portfolio", "all") and summary is not None:
                parts.append(format_portfolio_markdown(summary, eff_user_id))
            if intent in ("watchlist", "all"):
                parts.append(format_watchlist_markdown(watchlist_items, eff_user_id))

            formatted = "\n\n---\n\n".join(parts) if parts else (err or "Không có dữ liệu.")
            box["output"] = {
                "nav": getattr(summary, "total_nav", None),
                "watchlist_count": len(watchlist_items),
                "error": err,
            }
            return PortfolioWatchAgentResult(
                user_id=eff_user_id,
                intent=intent,
                portfolio_summary=summary,
                watchlist_items=watchlist_items,
                formatted_markdown=formatted,
                error=err,
            )
        except Exception as fatal_exc:
            _logger.exception("Lỗi nghiêm trọng trong run_portfolio_watch_agent: %s", fatal_exc)
            box["output"] = {"error": str(fatal_exc)}
            return PortfolioWatchAgentResult(
                user_id=eff_user_id,
                intent=intent,
                portfolio_summary=None,
                watchlist_items=[],
                formatted_markdown=f"Đã xảy ra lỗi khi kiểm tra thông tin danh mục/watchlist: {fatal_exc}",
                error=str(fatal_exc),
            )
