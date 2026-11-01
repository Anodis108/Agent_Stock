"""Node riêng của team scan (agent = subgraph make_agent_graph — tool + state ở <agent>/).

  1. Ngưỡng quét   — resolve_scan_threshold (entry run_graph / context)
  2. HITL          — propose_action, has_pending_action
  3. Node LLM      — event_classifier_node, synthesis_node
"""

from __future__ import annotations

import re
import uuid
from typing import Any

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import get_runtime

from ai_backend.domain.agents.scan.state import ScanHierarchicalState
from ai_backend.domain.guardrails.output_checks import strip_buy_sell
from ai_backend.infra.cache.tiered import chat_parsed_cached
from ai_backend.infra.llm.params import DETERMINISTIC
from ai_backend.infra.monitoring.tracing import current_span, trace_step
from ai_backend.infra.prompts import registry
from ai_backend.shared.settings import ai_settings
from common.domain.entities import AlertStatus, FinalAlert
from common.transport.schemas import ClassifierOutput, SynthesisAlertOutput

DEFAULT_THRESHOLD_PCT = 3.0


def resolve_scan_threshold(sym: str, user_id: str | None, deps: dict) -> float:
    """deps.threshold_pct → watchlist → config mặc định (chỉ dùng khi bootstrap task / response)."""
    threshold = deps["threshold_pct"]
    if threshold is None:
        store = deps["watchlist_store"]
        if store is not None:
            try:
                item = store.get(user_id, sym)
                threshold = item.threshold_pct if item else None
            except Exception:  # noqa: BLE001
                pass
    if threshold is None:
        configured = ai_settings.scan_default_threshold_pct
        threshold = configured if configured is not None else DEFAULT_THRESHOLD_PCT
    return float(threshold)


def _threshold_from_context(state: ScanHierarchicalState) -> float:
    """Ngưỡng cho prompt khi không lưu trên state — đọc context hoặc parse từ ``task``."""
    ctx = get_runtime().context
    raw = ctx["threshold_pct"]
    if raw is not None:
        return float(raw)
    task = state["task"] or ""
    m = re.search(r"ngưỡng biến động\s+([\d.]+)\s*%", task, re.IGNORECASE)
    if m:
        return float(m.group(1))
    configured = ai_settings.scan_default_threshold_pct
    return float(configured if configured is not None else DEFAULT_THRESHOLD_PCT)



# ── 2. HITL (như llm-engineer-demo, chỉ eval_agent → update_watchlist): hành động có side-effect = AIMessage.tool_calls
#    trong `messages`; graph dừng trước scan_tools (interrupt_before) chờ người duyệt. Cảnh báo gửi ngay, không qua đây.


def propose_action(name: str, args: dict[str, Any]) -> AIMessage:
    """Đề xuất hành động cần người duyệt — scan_tools thực thi sau khi duyệt."""
    return AIMessage(content="", tool_calls=[{"id": f"call_{uuid.uuid4().hex[:12]}", "name": name, "args": args}])


# ── 3. Node LLM (không phải agent: không tool, 1 lời gọi structured output) ──


def _row_for(items: list, sym: str):
    return next((x for x in items or [] if (x.symbol or "").upper() == sym.upper()), None)


def _evals(state: ScanHierarchicalState) -> list:
    if "eval_results" in state and state["eval_results"]:
        return list(state["eval_results"])
    ev = state["eval_result"] if "eval_result" in state else None
    return [ev] if ev is not None else []


def _eval_for(state: ScanHierarchicalState, index: int):
    """eval_results cùng thứ tự symbols; không có thì eval_result của đúng mã đầu."""
    evals = _evals(state)
    if index < len(evals):
        return evals[index]
    return None


async def event_classifier_node(state: ScanHierarchicalState, config: RunnableConfig) -> dict:
    """LLM phân loại lần lượt từng mã (giá + tin, ngưỡng) bình thường / bất thường."""
    routings = []
    lines = []
    threshold = f"{_threshold_from_context(state)}"
    for sym in state["symbols"]:
        price = _row_for(state["prices"], sym)
        news = _row_for(state["news"], sym)
        titles = "; ".join(i.title for i in (news.items if news else [])[:10]) or "(không có tin)"
        prompt = registry().render(
            "event_classification",
            version="production",
            symbol=sym,
            latest_close=f"{price.latest_close}" if price else "N/A",
            change_pct=f"{price.change_pct}" if price else "N/A",
            threshold_pct=threshold,
            news_titles=titles,
        )
        with trace_step(current_span(), "event_classifier", input=sym, as_type="generation") as box:
            out = chat_parsed_cached([{"role": "user", "content": prompt}], ClassifierOutput, DETERMINISTIC)
            routing = out.to_routing_decision()
            box["output"] = {"symbol": sym, "route": routing.route.value, "reason": routing.reason}
        routings.append(routing)
        lines.append(f"{routing.route.value} — {routing.reason}")
    done = {"event_routings": routings, "result": "; ".join(lines)}
    if routings:
        done["event_routing"] = routings[-1]
    return done


async def synthesis_node(state: ScanHierarchicalState, config: RunnableConfig) -> dict:
    """LLM soạn cảnh báo lần lượt từng mã đã có đánh giá → gửi ngay qua notifier + ghi ``alerts``."""
    alerts = []
    lines = []
    for index, sym in enumerate(state["symbols"]):
        ev = _eval_for(state, index)
        if ev is None:
            continue
        severity = ev.severity
        prompt = registry().render(
            "synthesis_alert",
            version="production",
            symbol=sym,
            severity_level=severity.level.value,
            confidence=f"{severity.confidence:.2f}",
            reasoning=severity.reasoning,
            evidence="; ".join(severity.evidence) or "(không có evidence)",
            preferences="(mặc định)",
            violations="(không)",
        )
        with trace_step(current_span(), "synthesis_agent", input=sym, as_type="generation") as box:
            out = chat_parsed_cached([{"role": "user", "content": prompt}], SynthesisAlertOutput, DETERMINISTIC)
            alert = FinalAlert(
                id=str(uuid.uuid4()),
                symbol=sym,
                title=out.title,
                body=strip_buy_sell(out.body),
                severity=severity,
                status=AlertStatus.DRAFT,
                metadata={"user_id": state["user_id"]},
            )
            get_runtime().context["notifier"].send(alert)
            box["output"] = {"alert_id": alert.id, "title": alert.title, "status": alert.status.value}
        alerts.append(alert)
        lines.append(f"đã gửi cảnh báo '{alert.title}'")
    done = {"alerts": alerts, "result": "; ".join(lines)}
    if alerts:
        done["alert"] = alerts[-1]
    return done
