"""Luồng giám sát 1 mã: Price+News → Classifier → Eval → Synthesis → Gate."""

from __future__ import annotations

import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any

from src.portfolio_watch.domain.agents.event_classifier import (
    EventClassifierBrain,
    classify_event,
)
from src.portfolio_watch.domain.agents.eval_agent import (
    EvalAgentBrain,
    EvalAgentResult,
    run_eval_agent,
)
from src.portfolio_watch.domain.agents.news_agent import (
    NewsAgentBrain,
    NewsAgentResult,
    default_news_brain,
    run_news_agent,
)
from src.portfolio_watch.domain.agents.price_agent import (
    PriceAgentResult,
    run_price_agent,
)
from src.portfolio_watch.domain.agents.synthesis_agent import (
    AlertComposer,
    SynthesisResult,
    run_synthesis_agent,
)
from src.portfolio_watch.domain.entities import (
    AlertStatus,
    EventRoute,
    FinalAlert,
    RoutingDecision,
    Severity,
)
from src.portfolio_watch.domain.ports import (
    MemoryStore,
    NewsSource,
    Notifier,
    PriceHistoryStore,
    PriceSource,
    WatchlistStore,
)
from src.portfolio_watch.infra.monitoring.tracing import agent_span, trace_request
from src.portfolio_watch.shared.logging import get_logger

# Confidence Gate: tin cậy cao VÀ |change_pct| khớp ngưỡng user
CONFIDENCE_AUTO_SEND = 0.8
DEFAULT_THRESHOLD_PCT = 3.0

_logger = get_logger(__name__)


@dataclass(slots=True)
class ScanSymbolResult:
    symbol: str
    price: PriceAgentResult
    news: NewsAgentResult
    routing: RoutingDecision
    threshold_pct: float
    severity: Severity | None = None
    alert: FinalAlert | None = None
    gate1_action: str | None = None  # "sent" | "pending_approval"
    gate2_pending: bool = False
    pending_events: list[dict] = field(default_factory=list)
    error: str | None = None


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
    """Confidence Gate: confidence >= 0.8 và |change_pct| >= ngưỡng user."""
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
    if not sym:
        empty_price = PriceAgentResult(
            symbol="",
            latest_close=None,
            prev_close=None,
            change_pct=None,
            error="symbol rỗng",
        )
        empty_news = NewsAgentResult(symbol="", items=[], error="symbol rỗng")
        return ScanSymbolResult(
            symbol="",
            price=empty_price,
            news=empty_news,
            routing=RoutingDecision(route=EventRoute.NORMAL, reason="symbol rỗng"),
            threshold_pct=DEFAULT_THRESHOLD_PCT,
            error="symbol rỗng",
        )

    thr = _resolve_threshold(sym, user_id, threshold_pct, watchlist_store)
    brain_news = news_brain or default_news_brain()
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
    with trace_request(
        "scan",
        sym,
        metadata=meta,
    ) as root:
        with ThreadPoolExecutor(max_workers=2) as pool:
            fut_price = pool.submit(run_price_agent, sym, price_source)
            fut_news = pool.submit(
                run_news_agent,
                sym,
                news_source,
                brain_news,
                days=news_days,
            )
            price = fut_price.result()
            news = fut_news.result()

        with agent_span(turn, "price_agent", input=sym) as box:
            box["output"] = {
                "close": price.latest_close,
                "change_pct": price.change_pct,
                "error": price.error,
            }

        with agent_span(turn, "news_agent", input=sym) as box:
            box["output"] = {
                "items": len(news.items or []),
                "error": news.error,
            }

        with agent_span(turn, "event_classifier", input=sym) as box:
            routing = classify_event(
                price, news, threshold_pct=thr, brain=classifier_brain
            )
            box["output"] = {
                "route": str(getattr(routing.route, "value", routing.route)),
                "reason": routing.reason,
            }

        result = ScanSymbolResult(
            symbol=sym,
            price=price,
            news=news,
            routing=routing,
            threshold_pct=thr,
        )

        if not _is_abnormal(routing.route):
            _logger.info(
                "scan %s NORMAL — %s", sym, routing.reason or "không escalate"
            )
            root["output"] = {"route": "normal", "symbol": sym}
            return result

        try:
            with agent_span(turn, "eval_agent", input=sym) as box:
                eval_result: EvalAgentResult = run_eval_agent(
                    price, news, history_store, brain=eval_brain
                )
                severity = eval_result.severity
                result.severity = severity
                box["output"] = str(severity)

            if _has_gate2_proposal(severity):
                gate2_event = {
                    "kind": "pending_approval",
                    "gate": "gate2",
                    "proposal_id": str(uuid.uuid4()),
                    "symbol": sym,
                    "status": AlertStatus.PENDING_APPROVAL.value,
                    "proposed_threshold_pct": severity.proposed_threshold_pct,
                    "proposed_related_symbols": list(
                        severity.proposed_related_symbols
                    ),
                    "severity": severity.model_dump(mode="json"),
                }
                memory_store.append_alert_event(user_id, gate2_event)
                result.gate2_pending = True
                result.pending_events.append(gate2_event)

            with agent_span(turn, "synthesis_agent", input=sym) as box:
                synthesis: SynthesisResult = run_synthesis_agent(
                    sym,
                    severity,
                    memory_store,
                    user_id=user_id,
                    composer=alert_composer,
                )
                alert = synthesis.alert
                if not alert.id:
                    alert.id = str(uuid.uuid4())
                alert.metadata = {**alert.metadata, "user_id": user_id}
                result.alert = alert
                box["output"] = {"alert_id": alert.id, "title": alert.title}

            if should_auto_send(severity, price, thr):
                try:
                    notifier.send(alert)
                    if alert.status != AlertStatus.SENT:
                        alert.status = AlertStatus.SENT
                    result.gate1_action = "sent"
                    _logger.info("scan %s Gate1 auto-send id=%s", sym, alert.id)
                except Exception as exc:  # noqa: BLE001 — không crash; về Gate 1
                    gate1_event = _append_gate1_pending(
                        memory_store, user_id, alert, sym
                    )
                    result.gate1_action = "pending_approval"
                    result.pending_events.append(gate1_event)
                    result.error = f"gửi cảnh báo lỗi, chuyển chờ duyệt: {exc}"
                    _logger.warning(
                        "scan %s auto-send failed → Gate1 pending: %s", sym, exc
                    )
            else:
                gate1_event = _append_gate1_pending(
                    memory_store, user_id, alert, sym
                )
                result.gate1_action = "pending_approval"
                result.pending_events.append(gate1_event)
                _logger.info("scan %s Gate1 pending id=%s", sym, alert.id)
        except Exception as exc:  # noqa: BLE001
            result.error = f"scan lỗi: {exc}"
            _logger.exception("scan %s failed: %s", sym, exc)

        root["output"] = {
            "symbol": sym,
            "route": str(getattr(routing.route, "value", routing.route)),
            "gate1_action": result.gate1_action,
            "error": result.error,
        }
        return result
