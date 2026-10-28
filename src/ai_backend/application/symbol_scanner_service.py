"""Symbol Scanner Service — Entrypoint nhánh scan của Hierarchical Swarm.

Kế thừa BaseService từ common.base.base_service.
Gọi `run_graph` (mode=scan) → top_supervisor → scan_supervisor điều phối
price/news → event_classifier → eval → synthesis; đề xuất update_watchlist dừng chờ duyệt (alert chỉ trên response)
(interrupt_before scan_tools) → `resume` (resume_graph) để duyệt / từ chối.
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any
from pydantic import Field

from common.base.base_model import CustomBaseModel
from common.base.base_service import BaseService
from common.domain.ports import MemoryStore, NewsSource, Notifier, PriceHistoryStore, PriceSource, WatchlistStore
from ai_backend.shared.logging import get_logger
from ai_backend.domain.agents.graph import resume_graph, start_graph


logger = get_logger("ai_backend.application.symbol_scanner")

DEFAULT_THRESHOLD_PCT = 3.0


class SymbolScannerInput(CustomBaseModel):
    """Input payload cho Symbol Scanner Service."""
    symbol: str
    user_id: str = "default"
    threshold_pct: float = DEFAULT_THRESHOLD_PCT
    request_id: str | None = None


class SymbolScannerOutput(CustomBaseModel):
    """Output payload từ Symbol Scanner Service."""
    symbol: str
    route: str = "technical"
    threshold_pct: float = DEFAULT_THRESHOLD_PCT
    change_pct: float = 0.0
    triggered: bool = False
    reason: str = ""
    status: str = "done"  # done | pending_approval
    thread_id: str = ""
    tool_call: dict[str, Any] | None = None
    alerts: list[dict[str, Any]] = Field(default_factory=list)
    steps: list[dict[str, Any]] = Field(default_factory=list)
    severity: dict[str, Any] | None = None
    alert: dict[str, Any] | None = None
    news_count: int = 0
    error: str | None = None
    request_id: str | None = None


class ScanResumeInput(CustomBaseModel):
    """Duyệt / từ chối hành động scan đang chờ (giống demo /assistant/approve)."""
    thread_id: str
    approve: bool
    reason: str = ""
    user_id: str = "default"


class ScanResumeOutput(CustomBaseModel):
    """Kết quả sau resume: done, hoặc lại pending_approval ở hành động kế tiếp."""
    symbol: str = ""
    status: str = "done"  # done | pending_approval
    thread_id: str = ""
    tool_call: dict[str, Any] | None = None
    alert: dict[str, Any] | None = None
    steps: list[dict[str, Any]] = Field(default_factory=list)
    error: str | None = None


class SymbolScannerService(BaseService):
    """Service quét cảnh báo một mã cổ phiếu qua Hierarchical Swarm Graph."""

    def __init__(
        self,
        *,
        price_source: PriceSource | None = None,
        news_source: NewsSource | None = None,
        history_store: PriceHistoryStore | None = None,
        memory_store: MemoryStore | None = None,
        watchlist_store: WatchlistStore | None = None,
        notifier: Notifier | None = None,
    ) -> None:
        self.price_source = price_source
        self.news_source = news_source
        self.history_store = history_store
        self.memory_store = memory_store
        self.watchlist_store = watchlist_store
        self.notifier = notifier

    def process(self, inputs: SymbolScannerInput) -> SymbolScannerOutput:
        """Quét 1 mã: lấy giá + tin, phân loại sự kiện, đánh giá mức độ, soạn cảnh báo và qua cổng HITL."""
        sym = inputs.symbol.strip().upper()
        req_id = inputs.request_id or str(uuid.uuid4())
        threshold = inputs.threshold_pct
        logger.info(f"SymbolScannerService.process: sym='{sym}' threshold={threshold} user='{inputs.user_id}'")

        deps = {
            "price_source": self.price_source,
            "news_source": self.news_source,
            "history_store": self.history_store,
            "memory_store": self.memory_store,
            "notifier": self.notifier,
            "watchlist_store": self.watchlist_store,
            "threshold_pct": threshold,
        }

        async def _run() -> Any:
            async for kind, payload in start_graph(
                "scan", sym, deps, user_id=inputs.user_id, request_id=req_id
            ):
                if kind == "result":
                    return payload
            raise RuntimeError("start_graph không yield result")

        from ai_backend.domain.agents.scan.nodes import DEFAULT_THRESHOLD_PCT
        from ai_backend.domain.agents.scan.state import main_item

        state = asyncio.run(_run())
        routing = state["event_routing"]
        route_obj = routing.route if routing is not None else None
        route = str(getattr(route_obj, "value", route_obj or "bình thường"))
        reason = routing.reason if routing is not None else ""
        prices = state["prices"] or []
        p = main_item(prices, state) if prices else None
        price = (
            None
            if p is None
            else {
                "symbol": p.symbol,
                "latest_close": p.latest_close,
                "prev_close": p.prev_close,
                "change_pct": p.change_pct,
                "error": p.error,
            }
        )
        change_pct = float(price["change_pct"] if price and price["change_pct"] is not None else 0.0)
        pct = state["threshold_pct"]
        threshold = pct if pct is not None else DEFAULT_THRESHOLD_PCT
        triggered = route_obj is not None and route in ("bất thường", "abnormal")
        news = main_item(state["news"] or [], state) if state["news"] else None
        ev = state["eval_result"]
        alert = state["alert"]
        return SymbolScannerOutput(
            symbol=sym,
            route=route,
            threshold_pct=threshold,
            change_pct=change_pct,
            triggered=triggered,
            reason=reason or "",
            status="pending_approval" if state["pending_tool_call"] else "done",
            thread_id=state["thread_id"] or "",
            tool_call=state["pending_tool_call"],
            alerts=[{
                "symbol": sym,
                "route": route,
                "threshold_pct": threshold,
                "change_pct": change_pct,
                "triggered": triggered,
                "reason": reason or "",
            }],
            severity=ev.severity.model_dump(mode="json") if ev is not None else None,
            alert=alert.model_dump(mode="json") if alert is not None else None,
            news_count=len(news.items) if news and news.items else 0,
            error=state["error"],
            request_id=req_id,
        )

    def resume(self, inputs: ScanResumeInput) -> ScanResumeOutput:
        """Duyệt → scan_tools chạy (cập nhật watchlist); từ chối → bỏ qua tool, graph chạy tiếp."""
        logger.info(f"SymbolScannerService.resume: thread='{inputs.thread_id}' approve={inputs.approve}")
        state = asyncio.run(resume_graph(
            inputs.thread_id,
            inputs.approve,
            inputs.reason,
            {  # đủ port như process(): sau khi duyệt, scan_supervisor vẫn có thể gọi thêm worker
                "price_source": self.price_source,
                "news_source": self.news_source,
                "history_store": self.history_store,
                "memory_store": self.memory_store,
                "notifier": self.notifier,
                "watchlist_store": self.watchlist_store,
            },
        ))
        symbols = state["symbols"]
        alert = state["alert"]
        return ScanResumeOutput(
            symbol=symbols[0] if symbols else "",
            status="pending_approval" if state["pending_tool_call"] else "done",
            thread_id=state["thread_id"] or "",
            tool_call=state["pending_tool_call"],
            alert=alert.model_dump(mode="json") if alert is not None else None,
            error=state["error"],
        )

    def scan(
        self,
        symbol: str,
        user_id: str = "default",
        threshold_pct: float = DEFAULT_THRESHOLD_PCT,
        request_id: str | None = None,
    ) -> Any:
        """Helper gọi từ API router trả về đối tượng tương thích ScanResponse."""
        from ai_backend.api.models.scan_models import ScanAlertOut, ScanResponse

        out = self.process(
            SymbolScannerInput(symbol=symbol, user_id=user_id, threshold_pct=threshold_pct, request_id=request_id)
        )
        return ScanResponse(
            symbol=out.symbol,
            route=out.route,
            threshold_pct=out.threshold_pct,
            reason=out.reason,
            status=out.status,
            thread_id=out.thread_id,
            tool_call=out.tool_call,
            error=out.error,
            request_id=out.request_id,
            alerts=[ScanAlertOut(**a) for a in out.alerts],
            steps=out.steps,
            severity=out.severity,
            alert=out.alert,
            news_count=out.news_count,
        )
