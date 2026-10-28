"""Symbol Scanner Service — Entrypoint nhánh scan của Hierarchical Swarm.

Kế thừa BaseService từ common.base.base_service.
Gọi `run_graph` (mode=scan) → top_supervisor → scan_supervisor điều phối
price/news → event_classifier → eval → synthesis; đề xuất update_watchlist dừng chờ duyệt (alert chỉ trên response)
(interrupt_before scan_tools) → `resume` (resume_graph) để duyệt / từ chối.
"""

from __future__ import annotations

import asyncio
from typing import Any
from pydantic import Field

from common.base.base_model import CustomBaseModel
from common.base.base_service import BaseService
from common.domain.ports import MemoryStore, NewsSource, Notifier, PriceHistoryStore, PriceSource, WatchlistStore
from ai_backend.shared.logging import get_logger
from ai_backend.domain.agents.graph import resume_graph, start_graph
from ai_backend.domain.agents.scan.nodes import DEFAULT_THRESHOLD_PCT

logger = get_logger("ai_backend.application.scan_service")

DEFAULT_THRESHOLD_PCT = 3.0


class ScanInput(CustomBaseModel):
    """Input payload cho scan service."""
    symbol: list[str]
    user_id: str
    threshold_pct: float = DEFAULT_THRESHOLD_PCT
    request_id: str


class ScanOutput(CustomBaseModel):
    """Output payload từ scan service."""
    symbol: list[str]
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
    request_id: str | None = None


class ScanResumeInput(CustomBaseModel):
    """Duyệt / từ chối hành động scan đang chờ (giống demo /assistant/approve)."""
    thread_id: str
    approve: bool
    reason: str = ""
    user_id: str


class ScanResumeOutput(CustomBaseModel):
    """Kết quả sau resume: done, hoặc lại pending_approval ở hành động kế tiếp."""
    symbol: str = ""
    status: str = "done"  # done | pending_approval
    thread_id: str = ""
    tool_call: dict[str, Any] | None = None
    alert: dict[str, Any] | None = None
    steps: list[dict[str, Any]] = Field(default_factory=list)


def _symbol_view(state: dict[str, Any], sym: str, index: int) -> dict[str, Any]:
    """Một mã trong đúng lượt quét (routing/alert theo mã, không lấy symbols[0])."""
    routings = state["event_routings"] if "event_routings" in state and state["event_routings"] else []
    routing = routings[index] if index < len(routings) else None
    route_obj = routing.route if routing is not None else None
    route = str(getattr(route_obj, "value", route_obj or "bình thường"))
    reason = routing.reason if routing is not None else ""
    prices = state["prices"] if "prices" in state else []
    news_list = state["news"] if "news" in state else []
    price = next((x for x in (prices or []) if (x.symbol or "").upper() == sym), None)
    change_pct = float(price.change_pct if price is not None and price.change_pct is not None else 0.0)
    pct = state["threshold_pct"] if "threshold_pct" in state else None
    news = next((x for x in (news_list or []) if (x.symbol or "").upper() == sym), None)
    evals = state["eval_results"] if "eval_results" in state and state["eval_results"] else []
    ev = evals[index] if index < len(evals) else None
    if ev is None and index == 0 and "eval_result" in state:
        ev = state["eval_result"]
    alerts = state["alerts"] if "alerts" in state and state["alerts"] else []
    alert = next((a for a in alerts if (a.symbol or "").upper() == sym), None)
    lone = state["alert"] if "alert" in state else None
    if alert is None and lone is not None and (lone.symbol or "").upper() == sym:
        alert = lone
    return {
        "symbol": sym,
        "route": route,
        "threshold_pct": pct if pct is not None else DEFAULT_THRESHOLD_PCT,
        "change_pct": change_pct,
        "triggered": route_obj is not None and route in ("bất thường", "abnormal"),
        "reason": reason or "",
        "status": "pending_approval" if ("pending_tool_call" in state and state["pending_tool_call"]) else "done",
        "thread_id": (state["thread_id"] or "") if "thread_id" in state else "",
        "tool_call": state["pending_tool_call"] if "pending_tool_call" in state else None,
        "severity": ev.severity.model_dump(mode="json") if ev is not None else None,
        "alert": alert.model_dump(mode="json") if alert is not None else None,
        "news_count": len(news.items) if news is not None and news.items else 0,
    }


class ScanService(BaseService):
    """Service quét cảnh báo các mã cổ phiếu qua Hierarchical Swarm Graph."""

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

    def process(self, inputs: ScanInput) -> ScanOutput:
        """Một lượt graph: mỗi bước agent đi hết danh sách mã rồi mới sang bước sau."""
        symbols = [s.strip().upper() for s in inputs.symbol if s.strip()]
        if not symbols:
            raise ValueError("cần ít nhất một mã")

        deps = {
            "price_source": self.price_source,
            "news_source": self.news_source,
            "history_store": self.history_store,
            "memory_store": self.memory_store,
            "notifier": self.notifier,
            "watchlist_store": self.watchlist_store,
            "threshold_pct": inputs.threshold_pct,
        }

        async def _run() -> dict[str, Any]:
            state = None
            async for kind, payload in start_graph(
                "scan", ",".join(symbols), deps, user_id=inputs.user_id, request_id=inputs.request_id
            ):
                if kind == "result":
                    state = payload
            if state is None:
                raise RuntimeError("start_graph không yield result")
            return state

        state = asyncio.run(_run())
        ordered = [s for s in (state["symbols"] or symbols) if s]
        rows = [_symbol_view(state, sym, i) for i, sym in enumerate(ordered)]
        pending = [r for r in rows if r["status"] == "pending_approval"]
        one = rows[0] if len(rows) == 1 else None
        return ScanOutput(
            symbol=symbols,
            route=one["route"] if one else ("bất thường" if any(r["triggered"] for r in rows) else "bình thường"),
            threshold_pct=one["threshold_pct"] if one else inputs.threshold_pct,
            change_pct=one["change_pct"] if one else 0.0,
            triggered=any(r["triggered"] for r in rows),
            reason="; ".join(r["reason"] for r in rows if r["reason"]),
            status="pending_approval" if pending else "done",
            thread_id=pending[0]["thread_id"] if len(pending) == 1 else (one["thread_id"] if one else ""),
            tool_call=pending[0]["tool_call"] if len(pending) == 1 else (one["tool_call"] if one else None),
            alerts=[
                {
                    "symbol": r["symbol"],
                    "route": r["route"],
                    "threshold_pct": r["threshold_pct"],
                    "change_pct": r["change_pct"],
                    "triggered": r["triggered"],
                    "reason": r["reason"],
                    "status": r["status"],
                    "thread_id": r["thread_id"],
                    "tool_call": r["tool_call"],
                    "alert": r["alert"],
                }
                for r in rows
            ],
            severity=one["severity"] if one else None,
            alert=one["alert"] if one else None,
            news_count=sum(r["news_count"] for r in rows),
            request_id=inputs.request_id,
        )

    def resume(self, inputs: ScanResumeInput) -> ScanResumeOutput:
        """Duyệt → scan_tools chạy (cập nhật watchlist); từ chối → bỏ qua tool, graph chạy tiếp."""
        logger.info(f"ScanService.resume: thread='{inputs.thread_id}' approve={inputs.approve}")
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
        symbols = [s for s in (state["symbols"] or []) if s]
        alert = state["alert"]
        return ScanResumeOutput(
            symbol=", ".join(symbols),
            status="pending_approval" if state["pending_tool_call"] else "done",
            thread_id=state["thread_id"] or "",
            tool_call=state["pending_tool_call"],
            alert=alert.model_dump(mode="json") if alert is not None else None,
        )

    def scan(
        self,
        symbol: list[str],
        user_id: str,
        request_id: str,
        threshold_pct: float = DEFAULT_THRESHOLD_PCT,
    ) -> Any:
        """Helper gọi từ API router trả về đối tượng tương thích ScanResponse."""
        from ai_backend.api.models.scan_models import ScanAlertOut, ScanResponse

        out = self.process(
            ScanInput(symbol=symbol, user_id=user_id, threshold_pct=threshold_pct, request_id=request_id)
        )
        return ScanResponse(
            symbol=out.symbol,
            route=out.route,
            threshold_pct=out.threshold_pct,
            reason=out.reason,
            status=out.status,
            thread_id=out.thread_id,
            tool_call=out.tool_call,
            request_id=out.request_id,
            alerts=[ScanAlertOut(**a) for a in out.alerts],
            steps=out.steps,
            severity=out.severity,
            alert=out.alert,
            news_count=out.news_count,
        )
