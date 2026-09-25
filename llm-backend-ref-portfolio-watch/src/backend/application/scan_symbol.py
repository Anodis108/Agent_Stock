"""Luồng giám sát 1 mã — wrapper gọi LangGraph scan; giữ helpers + contract."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from backend.agents.event_classifier import EventClassifierBrain
from backend.agents.eval_agent import EvalAgentBrain
from backend.agents.news_agent import NewsAgentBrain, NewsAgentResult
from backend.agents.price_agent import PriceAgentResult
from backend.agents.synthesis_agent import AlertComposer
from backend.domain.entities import (
    AlertStatus,
    EventRoute,
    FinalAlert,
    RoutingDecision,
    Severity,
)
from backend.domain.ports import (
    MemoryStore,
    NewsSource,
    Notifier,
    PriceHistoryStore,
    PriceSource,
    WatchlistStore,
)
from backend.infra.monitoring.tracing import trace_request

CONFIDENCE_AUTO_SEND = 0.8
DEFAULT_THRESHOLD_PCT = 3.0


@dataclass(slots=True)
class ScanSymbolResult:
    symbol: str
    price: PriceAgentResult
    news: NewsAgentResult
    routing: RoutingDecision
    threshold_pct: float
    severity: Severity | None = None
    alert: FinalAlert | None = None
    gate1_action: str | None = None
    gate2_pending: bool = False
    pending_events: list[dict] = field(default_factory=list)
    error: str | None = None
    steps: list[dict] = field(default_factory=list)


def _resolve_threshold(
    symbol: str,
    user_id: str,
    threshold_pct: float | None,
    watchlist_store: WatchlistStore | None,
) -> float:
    if threshold_pct is not None:
        return float(threshold_pct)
    if watchlist_store is not None:
        item = watchlist_store.get(user_id, symbol)
        if item is not None:
            return float(item.threshold_pct)
    return DEFAULT_THRESHOLD_PCT


def should_auto_send(
    severity: Severity,
    price: PriceAgentResult,
    threshold_pct: float,
) -> bool:
    if severity.confidence < CONFIDENCE_AUTO_SEND:
        return False
    if price.change_pct is None:
        return False
    thr = threshold_pct if threshold_pct > 0 else DEFAULT_THRESHOLD_PCT
    return abs(price.change_pct) >= thr


def _has_gate2_proposal(severity: Severity) -> bool:
    if severity.proposed_threshold_pct is not None:
        return True
    return bool(severity.proposed_related_symbols)


def _is_abnormal(route: EventRoute | str) -> bool:
    if route == EventRoute.ABNORMAL:
        return True
    return str(route) == EventRoute.ABNORMAL.value


def _append_gate1_pending(
    memory_store: MemoryStore,
    user_id: str,
    alert: FinalAlert,
    symbol: str,
) -> dict:
    alert.status = AlertStatus.PENDING_APPROVAL
    event = {
        "kind": "pending_approval",
        "gate": "gate1",
        "alert_id": alert.id,
        "symbol": symbol,
        "status": alert.status.value,
        "alert": alert.model_dump(mode="json"),
    }
    memory_store.append_alert_event(user_id, event)
    return event


def scan_symbol(
    symbol: str,
    *,
    price_source: PriceSource,
    news_source: NewsSource,
    history_store: PriceHistoryStore,
    memory_store: MemoryStore,
    notifier: Notifier,
    watchlist_store: WatchlistStore | None = None,
    user_id: str = "default",
    threshold_pct: float | None = None,
    request_id: str | None = None,
    news_brain: NewsAgentBrain | None = None,
    classifier_brain: EventClassifierBrain | None = None,
    eval_brain: EvalAgentBrain | None = None,
    alert_composer: AlertComposer | None = None,
    news_days: int | None = 7,
) -> ScanSymbolResult:
    sym = (symbol or "").strip().upper()
    rid = (request_id or "").strip() or None
    turn = rid or str(uuid.uuid4())
    meta: dict[str, Any] = {
        "turn": turn,
        "user_id": user_id,
        "kind": "scan",
        "symbol": sym,
    }
    if rid:
        meta["request_id"] = rid

    with trace_request("scan", sym, metadata=meta) as root:
        from backend.graph.scan import run_scan_graph

        result = run_scan_graph(
            symbol=sym,
            price_source=price_source,
            news_source=news_source,
            history_store=history_store,
            memory_store=memory_store,
            notifier=notifier,
            watchlist_store=watchlist_store,
            user_id=user_id,
            threshold_pct=threshold_pct,
            request_id=request_id,
            turn=turn,
            news_brain=news_brain,
            classifier_brain=classifier_brain,
            eval_brain=eval_brain,
            alert_composer=alert_composer,
            news_days=news_days,
        )

        root["output"] = {
            "symbol": sym,
            "route": str(getattr(result.routing.route, "value", result.routing.route)),
            "gate1_action": result.gate1_action,
            "error": result.error,
        }
        return result
