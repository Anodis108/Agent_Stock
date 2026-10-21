"""Team scan của Hierarchical Swarm — các node riêng của nhánh quét cảnh báo + entrypoint `run_scan_graph`.

Graph dựng ở graph.py; scan_supervisor quyết định từng bước:
price_agent + news_agent (worker dùng chung) → event_classifier → (bình thường: END)
→ eval_agent → [hitl_gate_2 nếu có đề xuất] → synthesis_agent → hitl_gate_1 (tự gửi | chờ duyệt) → END
"""

from __future__ import annotations

import uuid
from typing import Any

from langchain_core.runnables import RunnableConfig

from dataclasses import dataclass, field

@dataclass(slots=True)
class ScanSymbolResult:
    symbol: str
    price: Any
    news: Any
    routing: Any
    threshold_pct: float
    severity: Any | None = None
    alert: Any | None = None
    gate1_action: str | None = None
    gate2_pending: bool = False
    pending_events: list[dict] = field(default_factory=list)
    error: str | None = None
    steps: list[dict] = field(default_factory=list)


def _resolve_threshold(
    symbol: str,
    user_id: str,
    threshold_pct: float | None,
    watchlist_store: Any | None,
) -> float:
    if threshold_pct is not None:
        return float(threshold_pct)
    if watchlist_store is not None:
        try:
            item = watchlist_store.get(user_id, symbol)
            if item is not None:
                return float(getattr(item, "threshold_pct", 3.0))
        except Exception:
            pass
    return 3.0


def should_auto_send(
    severity: Any,
    price: Any,
    threshold_pct: float,
) -> bool:
    if getattr(severity, "confidence", 0.0) < 0.8:
        return False
    if getattr(price, "change_pct", None) is None:
        return False
    thr = threshold_pct if threshold_pct > 0 else 3.0
    return abs(price.change_pct) >= thr


def has_gate2_proposal(severity: Any) -> bool:
    if getattr(severity, "proposed_threshold_pct", None) is not None:
        return True
    return bool(getattr(severity, "proposed_related_symbols", None))


def is_abnormal(route: Any) -> bool:
    # EventRoute.ABNORMAL.value là "bất thường"; vẫn nhận "abnormal" từ LLM / dữ liệu cũ
    return str(getattr(route, "value", route)).lower() in ("bất thường", "abnormal")


def _append_gate1_pending(
    memory_store: Any,
    user_id: str,
    alert: Any,
    symbol: str,
) -> dict:
    from common.domain.entities import AlertStatus
    alert.status = AlertStatus.PENDING_APPROVAL
    event = {
        "kind": "pending_approval",
        "gate": "gate1",
        "alert_id": getattr(alert, "id", ""),
        "symbol": symbol,
        "status": getattr(alert.status, "value", "pending_approval"),
        "alert": alert.model_dump(mode="json") if hasattr(alert, "model_dump") else str(alert),
    }
    if hasattr(memory_store, "append_alert_event"):
        memory_store.append_alert_event(user_id, event)
    return event

from ai_backend.infra.agents.scan.event_classifier import (
    EventClassifierBrain,
    classify_event,
)
from ai_backend.infra.agents.scan.eval_agent import EvalAgentBrain
from ai_backend.infra.agents.scan.news_agent import NewsAgentBrain, NewsAgentResult
from ai_backend.infra.agents.scan.price_agent import PriceAgentResult
from ai_backend.infra.agents.scan.synthesis_agent import AlertComposer, run_synthesis_agent
from common.domain.entities import (
    AlertStatus,
    EventRoute,
    RoutingDecision,
)
from common.domain.ports import (
    MemoryStore,
    NewsSource,
    Notifier,
    PriceHistoryStore,
    PriceSource,
    WatchlistStore,
)
from ai_backend.infra.agents.events import graph_deps
from ai_backend.infra.agents.state import SwarmState
from ai_backend.infra.monitoring.tracing import agent_span
from common.logging import get_logger

_logger = get_logger(__name__)
DEFAULT_THRESHOLD_PCT = 3.0
def _cfg(_config: RunnableConfig) -> dict[str, Any]:
    return graph_deps.get()


def event_classifier_node(state: SwarmState, config: RunnableConfig) -> dict:
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
    return {"event_routing": routing}


def hitl_gate_2_node(state: SwarmState, config: RunnableConfig) -> dict:
    cfg = _cfg(config)
    sym = state["symbol"]
    turn = state.get("turn") or ""
    user_id = state.get("user_id") or "default"
    severity = state["severity"]
    memory_store: MemoryStore = cfg["memory_store"]
    with agent_span(turn, "confidence_gate", input={"symbol": sym, "gate": "gate2"}) as box:
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
        box["output"] = {"gate2_pending": True, "proposal_id": gate2_event["proposal_id"]}
    return {"gate2_pending": True, "pending_events": pending}


def synthesis_node(state: SwarmState, config: RunnableConfig) -> dict:
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
            box["output"] = {
                "alert_id": alert.id,
                "title": alert.title,
                "status": alert.status.value,
            }
        return {"alert": alert}
    except Exception as exc:  # noqa: BLE001
        _logger.exception("scan %s synthesis failed: %s", sym, exc)
        return {"error": f"scan lỗi: {exc}"}


def hitl_gate_1_node(state: SwarmState, config: RunnableConfig) -> dict:
    """Gate 1: đủ tin cậy + vượt ngưỡng -> tự gửi cảnh báo; ngược lại (hoặc gửi lỗi) -> chờ người duyệt."""
    cfg = _cfg(config)
    alert = state["alert"]
    sym = state["symbol"]
    turn = state.get("turn") or ""
    user_id = state.get("user_id") or "default"
    thr = state.get("threshold_pct") or DEFAULT_THRESHOLD_PCT
    pending = list(state.get("pending_events") or [])

    with agent_span(turn, "confidence_gate", input={"symbol": sym, "gate": "gate1"}) as box:
        if should_auto_send(state.get("severity"), state.get("price"), thr):
            notifier: Notifier = cfg["notifier"]
            try:
                notifier.send(alert)
                if alert.status != AlertStatus.SENT:
                    alert.status = AlertStatus.SENT
                box["output"] = {"gate1_action": "sent", "alert_id": alert.id}
                return {"gate1_action": "sent", "alert": alert}
            except Exception as exc:  # noqa: BLE001
                _logger.warning("scan %s auto-send failed → Gate1 pending: %s", sym, exc)
                pending.append(_append_gate1_pending(cfg["memory_store"], user_id, alert, sym))
                box["output"] = {"gate1_action": "pending_approval", "alert_id": alert.id, "error": str(exc)}
                return {
                    "gate1_action": "pending_approval",
                    "pending_events": pending,
                    "error": f"gửi cảnh báo lỗi, chuyển chờ duyệt: {exc}",
                    "alert": alert,
                }

        pending.append(_append_gate1_pending(cfg["memory_store"], user_id, alert, sym))
        box["output"] = {"gate1_action": "pending_approval", "alert_id": alert.id}
    return {"gate1_action": "pending_approval", "pending_events": pending, "alert": alert}


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
    """Quét một mã: giá/tin → phân loại → (nếu bất thường) eval / HITL / cảnh báo.

    Luồng tổng quát:
      1) Chuẩn hóa mã; mã rỗng → trả lỗi sớm
      2) Lấy ngưỡng cảnh báo + turn_id
      3) Gói deps + state → run_swarm_graph (mode=scan)
      4) Map state → ScanSymbolResult + steps timeline
    """
    # --- 1) Chuẩn hóa symbol; early return nếu rỗng ---
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

    # --- 2) Ngưỡng từ watchlist/arg + id lượt quét ---
    thr = _resolve_threshold(sym, user_id, threshold_pct, watchlist_store)
    turn_id = (turn or "").strip() or (request_id or "").strip() or str(uuid.uuid4())

    # --- 3) Chạy swarm graph (price/news → classifier → eval → HITL → synthesis) ---
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
    from ai_backend.infra.agents.graph import run_swarm_graph

    final, chunks, node_timings = run_swarm_graph(
        {
            "mode": "scan",
            "symbol": sym,
            "symbols": [sym],
            "user_id": user_id,
            "turn": turn_id,
            "threshold_pct": thr,
            "pending_events": [],
            "completed": [],
        },
        deps,
    )

    # --- 4) Map state graph → ScanSymbolResult + timeline steps ---
    result = ScanSymbolResult(
        symbol=sym,
        price=final.get("price"),
        news=final.get("news"),
        routing=final.get("event_routing"),
        threshold_pct=thr,
        severity=final.get("severity"),
        alert=final.get("alert"),
        gate1_action=final.get("gate1_action"),
        gate2_pending=bool(final.get("gate2_pending")),
        pending_events=list(final.get("pending_events") or []),
        error=final.get("error"),
    )

    from ai_backend.infra.agents.steps import build_steps_from_chunks
    result.steps = build_steps_from_chunks(
        chunks, final_error=result.error, timings=node_timings
    )

    _logger.info(
        "run_scan_graph %s route=%s gate1=%s",
        sym,
        getattr(getattr(result.routing, "route", None), "value", getattr(result.routing, "route", None)),
        result.gate1_action,
    )
    return result
