"""LangGraph scan — price+news → classifier → (normal END | abnormal pipeline)."""

from __future__ import annotations

import contextvars
import uuid
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from typing import Any, Literal

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph

from src.portfolio_watch.application.scan_symbol import (
    ScanSymbolResult,
    _append_gate1_pending,
    _has_gate2_proposal,
    _is_abnormal,
    _resolve_threshold,
    should_auto_send,
)
from src.portfolio_watch.domain.agents.event_classifier import (
    EventClassifierBrain,
    classify_event,
)
from src.portfolio_watch.domain.agents.eval_agent import EvalAgentBrain, run_eval_agent
from src.portfolio_watch.domain.agents.news_agent import (
    NewsAgentBrain,
    NewsAgentResult,
    default_news_brain,
    run_news_agent,
)
from src.portfolio_watch.domain.agents.price_agent import PriceAgentResult, run_price_agent
from src.portfolio_watch.domain.agents.synthesis_agent import AlertComposer, run_synthesis_agent
from src.portfolio_watch.domain.entities import (
    AlertStatus,
    EventRoute,
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
from src.portfolio_watch.graph.state import ScanState
from src.portfolio_watch.infra.monitoring.tracing import agent_span
from src.portfolio_watch.shared.logging import get_logger

_logger = get_logger(__name__)
DEFAULT_THRESHOLD_PCT = 3.0
_scan_deps: contextvars.ContextVar[dict[str, Any]] = contextvars.ContextVar(
    "_scan_deps", default={}
)


def _cfg(_config: RunnableConfig) -> dict[str, Any]:
    return _scan_deps.get()


def _node_fetch(state: ScanState, config: RunnableConfig) -> dict:
    cfg = _cfg(config)
    sym = state["symbol"]
    turn = state.get("turn") or ""
    price_source: PriceSource = cfg["price_source"]
    news_source: NewsSource = cfg["news_source"]
    news_brain: NewsAgentBrain | None = cfg.get("news_brain")
    news_days: int | None = cfg.get("news_days", 7)

    with ThreadPoolExecutor(max_workers=2) as pool:
        fut_price = pool.submit(run_price_agent, sym, price_source, turn)
        fut_news = pool.submit(
            run_news_agent,
            sym,
            news_source,
            news_brain or default_news_brain(),
            days=news_days,
            turn=turn,
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
        box["output"] = {"items": len(news.items or []), "error": news.error}

    return {"price": price, "news": news}


def _node_classifier(state: ScanState, config: RunnableConfig) -> dict:
    cfg = _cfg(config)
    turn = state.get("turn") or ""
    sym = state["symbol"]
    price = state["price"]
    news = state["news"]
    thr = state.get("threshold_pct") or DEFAULT_THRESHOLD_PCT
    classifier_brain: EventClassifierBrain | None = cfg.get("classifier_brain")

    with agent_span(turn, "event_classifier", input=sym) as box:
        routing = classify_event(
            price, news, threshold_pct=thr, brain=classifier_brain, turn=turn
        )
        box["output"] = {
            "route": str(getattr(routing.route, "value", routing.route)),
            "reason": routing.reason,
        }
    return {"routing": routing}


def _route_after_classifier(
    state: ScanState,
) -> Literal["eval_agent", "__end__"]:
    routing = state.get("routing")
    if routing is None or not _is_abnormal(routing.route):
        return END
    return "eval_agent"


def _node_eval(state: ScanState, config: RunnableConfig) -> dict:
    cfg = _cfg(config)
    turn = state.get("turn") or ""
    sym = state["symbol"]
    try:
        with agent_span(turn, "eval_agent", input=sym) as box:
            eval_result = run_eval_agent(
                state["price"],
                state["news"],
                cfg["history_store"],
                brain=cfg.get("eval_brain"),
                turn=turn,
            )
            box["output"] = str(eval_result.severity)
        return {"severity": eval_result.severity, "eval_result": eval_result}
    except Exception as exc:  # noqa: BLE001
        _logger.exception("scan %s eval failed: %s", sym, exc)
        return {"error": f"scan lỗi: {exc}"}


def _route_after_eval(
    state: ScanState,
) -> Literal["gate2", "synthesis_agent", "__end__"]:
    if state.get("error"):
        return END
    severity = state.get("severity")
    if severity is not None and _has_gate2_proposal(severity):
        return "gate2"
    return "synthesis_agent"


def _node_gate2(state: ScanState, config: RunnableConfig) -> dict:
    cfg = _cfg(config)
    sym = state["symbol"]
    user_id = state.get("user_id") or "default"
    severity = state["severity"]
    memory_store: MemoryStore = cfg["memory_store"]
    gate2_event = {
        "kind": "pending_approval",
        "gate": "gate2",
        "proposal_id": str(uuid.uuid4()),
        "symbol": sym,
        "status": AlertStatus.PENDING_APPROVAL.value,
        "proposed_threshold_pct": severity.proposed_threshold_pct,
        "proposed_related_symbols": list(severity.proposed_related_symbols),
        "severity": severity.model_dump(mode="json"),
    }
    memory_store.append_alert_event(user_id, gate2_event)
    pending = list(state.get("pending_events") or [])
    pending.append(gate2_event)
    return {"gate2_pending": True, "pending_events": pending}


def _node_synthesis(state: ScanState, config: RunnableConfig) -> dict:
    cfg = _cfg(config)
    turn = state.get("turn") or ""
    sym = state["symbol"]
    user_id = state.get("user_id") or "default"
    severity = state["severity"]
    memory_store: MemoryStore = cfg["memory_store"]
    composer: AlertComposer | None = cfg.get("alert_composer")

    try:
        with agent_span(turn, "synthesis_agent", input=sym) as box:
            synthesis = run_synthesis_agent(
                sym,
                severity,
                memory_store,
                user_id=user_id,
                composer=composer,
                turn=turn,
            )
            alert = synthesis.alert
            if not alert.id:
                alert.id = str(uuid.uuid4())
            alert.metadata = {**alert.metadata, "user_id": user_id}
            box["output"] = {"alert_id": alert.id, "title": alert.title}
        return {"alert": alert}
    except Exception as exc:  # noqa: BLE001
        _logger.exception("scan %s synthesis failed: %s", sym, exc)
        return {"error": f"scan lỗi: {exc}"}


def _route_after_synthesis(
    state: ScanState,
) -> Literal["gate1_auto", "gate1_pending", "__end__"]:
    if state.get("error") or state.get("alert") is None:
        return END
    severity = state.get("severity")
    price = state.get("price")
    thr = state.get("threshold_pct") or DEFAULT_THRESHOLD_PCT
    if severity is not None and price is not None and should_auto_send(severity, price, thr):
        return "gate1_auto"
    return "gate1_pending"


def _node_gate1_auto(state: ScanState, config: RunnableConfig) -> dict:
    cfg = _cfg(config)
    alert = state["alert"]
    notifier: Notifier = cfg["notifier"]
    sym = state["symbol"]
    try:
        notifier.send(alert)
        if alert.status != AlertStatus.SENT:
            alert.status = AlertStatus.SENT
        return {"gate1_action": "sent", "alert": alert}
    except Exception as exc:  # noqa: BLE001
        _logger.warning("scan %s auto-send failed → Gate1 pending: %s", sym, exc)
        gate1_event = _append_gate1_pending(
            cfg["memory_store"], state.get("user_id") or "default", alert, sym
        )
        pending = list(state.get("pending_events") or [])
        pending.append(gate1_event)
        return {
            "gate1_action": "pending_approval",
            "pending_events": pending,
            "error": f"gửi cảnh báo lỗi, chuyển chờ duyệt: {exc}",
            "alert": alert,
        }


def _node_gate1_pending(state: ScanState, config: RunnableConfig) -> dict:
    cfg = _cfg(config)
    sym = state["symbol"]
    alert = state["alert"]
    gate1_event = _append_gate1_pending(
        cfg["memory_store"], state.get("user_id") or "default", alert, sym
    )
    pending = list(state.get("pending_events") or [])
    pending.append(gate1_event)
    return {"gate1_action": "pending_approval", "pending_events": pending, "alert": alert}


def build_scan_graph() -> StateGraph:
    graph = StateGraph(ScanState)
    graph.add_node("fetch", _node_fetch)
    graph.add_node("event_classifier", _node_classifier)
    graph.add_node("eval_agent", _node_eval)
    graph.add_node("gate2", _node_gate2)
    graph.add_node("synthesis_agent", _node_synthesis)
    graph.add_node("gate1_auto", _node_gate1_auto)
    graph.add_node("gate1_pending", _node_gate1_pending)

    graph.add_edge(START, "fetch")
    graph.add_edge("fetch", "event_classifier")
    graph.add_conditional_edges(
        "event_classifier",
        _route_after_classifier,
        {"eval_agent": "eval_agent", END: END},
    )
    graph.add_conditional_edges(
        "eval_agent",
        _route_after_eval,
        {"gate2": "gate2", "synthesis_agent": "synthesis_agent", END: END},
    )
    graph.add_edge("gate2", "synthesis_agent")
    graph.add_conditional_edges(
        "synthesis_agent",
        _route_after_synthesis,
        {"gate1_auto": "gate1_auto", "gate1_pending": "gate1_pending", END: END},
    )
    graph.add_edge("gate1_auto", END)
    graph.add_edge("gate1_pending", END)
    return graph


@lru_cache(maxsize=1)
def compile_scan_graph():
    return build_scan_graph().compile()


def run_scan_graph(
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
    turn: str = "",
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
    turn_id = (turn or "").strip() or (request_id or "").strip() or str(uuid.uuid4())
    deps = {
        "price_source": price_source,
        "news_source": news_source,
        "history_store": history_store,
        "memory_store": memory_store,
        "notifier": notifier,
        "news_brain": news_brain,
        "classifier_brain": classifier_brain,
        "eval_brain": eval_brain,
        "alert_composer": alert_composer,
        "news_days": news_days,
    }
    token = _scan_deps.set(deps)
    try:
        final = {
            "symbol": sym,
            "user_id": user_id,
            "turn": turn_id,
            "threshold_pct": thr,
            "pending_events": [],
        }
        chunks = []
        for chunk in compile_scan_graph().stream(
            final,
            config=RunnableConfig(recursion_limit=25),
            stream_mode="updates",
        ):
            chunks.append(chunk)
            for node, values in chunk.items():
                final.update(values)
    finally:
        _scan_deps.reset(token)

    result = ScanSymbolResult(
        symbol=sym,
        price=final["price"],
        news=final["news"],
        routing=final["routing"],
        threshold_pct=thr,
        severity=final.get("severity"),
        alert=final.get("alert"),
        gate1_action=final.get("gate1_action"),
        gate2_pending=bool(final.get("gate2_pending")),
        pending_events=list(final.get("pending_events") or []),
        error=final.get("error"),
    )
    
    from src.portfolio_watch.graph.steps import build_steps_from_chunks
    result.steps = build_steps_from_chunks(chunks, final_error=result.error)

    _logger.info(
        "run_scan_graph %s route=%s gate1=%s",
        sym,
        getattr(result.routing.route, "value", result.routing.route),
        result.gate1_action,
    )
    return result
