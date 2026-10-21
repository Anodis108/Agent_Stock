"""Symbol Scanner Service — Entrypoint nhánh scan của Hierarchical Swarm.

Kế thừa BaseService từ common.base.base_service.
Gọi `graph_runner` (production: run_scan_graph) → top_supervisor → scan_supervisor điều phối
price/news → event_classifier → eval → synthesis → HITL gate 1/2.
Bắt buộc inject graph_runner; test truyền runner giả qua fixture.
"""

from __future__ import annotations

import uuid
from typing import Any, Callable
from pydantic import Field

from common.base.base_model import CustomBaseModel
from common.base.base_service import BaseService
from common.domain.ports import MemoryStore, NewsSource, Notifier, PriceHistoryStore, PriceSource, WatchlistStore
from common.logging.logger import get_logger
from ai_backend.infra.agents.scan.team import ScanSymbolResult


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
    gate1_action: str | None = None
    gate2_pending: bool = False
    pending_events: list[dict[str, Any]] = Field(default_factory=list)
    alerts: list[dict[str, Any]] = Field(default_factory=list)
    steps: list[dict[str, Any]] = Field(default_factory=list)
    severity: dict[str, Any] | None = None
    alert: dict[str, Any] | None = None
    news_count: int = 0
    error: str | None = None
    request_id: str | None = None


class SymbolScannerService(BaseService):
    """Service quét cảnh báo một mã cổ phiếu qua Hierarchical Swarm Graph."""

    def __init__(
        self,
        *,
        graph_runner: Callable[..., ScanSymbolResult] | None = None,  # production: run_scan_graph
        price_source: PriceSource | None = None,
        news_source: NewsSource | None = None,
        history_store: PriceHistoryStore | None = None,
        memory_store: MemoryStore | None = None,
        watchlist_store: WatchlistStore | None = None,
        notifier: Notifier | None = None,
    ) -> None:
        self.graph_runner = graph_runner
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
        threshold = float(inputs.threshold_pct) if inputs.threshold_pct is not None else DEFAULT_THRESHOLD_PCT
        logger.info(f"SymbolScannerService.process: sym='{sym}' threshold={threshold}% user='{inputs.user_id}'")

        if self.graph_runner is None:
            raise RuntimeError("SymbolScannerService chưa được inject graph_runner (run_scan_graph)")

        res = self.graph_runner(
            sym,
            price_source=self.price_source,
            news_source=self.news_source,
            history_store=self.history_store,
            memory_store=self.memory_store,
            notifier=self.notifier,
            watchlist_store=self.watchlist_store,
            user_id=inputs.user_id,
            threshold_pct=threshold,
            request_id=req_id,
        )
        route_obj = getattr(res.routing, "route", None)
        route = str(getattr(route_obj, "value", route_obj or "bình thường"))
        reason = getattr(res.routing, "reason", "") or ""
        change_pct = float(getattr(res.price, "change_pct", None) or 0.0)
        triggered = route_obj is not None and route in ("bất thường", "abnormal")
        return SymbolScannerOutput(
            symbol=sym,
            route=route,
            threshold_pct=res.threshold_pct,
            change_pct=change_pct,
            triggered=triggered,
            reason=reason,
            gate1_action=res.gate1_action,
            gate2_pending=res.gate2_pending,
            pending_events=res.pending_events,
            alerts=[{
                "symbol": sym,
                "route": route,
                "threshold_pct": res.threshold_pct,
                "change_pct": change_pct,
                "triggered": triggered,
                "reason": reason,
            }],
            steps=res.steps,
            severity=res.severity.model_dump(mode="json") if res.severity is not None else None,
            alert=res.alert.model_dump(mode="json") if res.alert is not None else None,
            news_count=len(getattr(res.news, "items", None) or []),
            error=res.error,
            request_id=req_id,
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
            gate1_action=out.gate1_action,
            gate2_pending=out.gate2_pending,
            error=out.error,
            request_id=out.request_id,
            alerts=[ScanAlertOut(**a) for a in out.alerts],
            steps=out.steps,
            severity=out.severity,
            alert=out.alert,
            news_count=out.news_count,
            pending_events=out.pending_events,
        )
