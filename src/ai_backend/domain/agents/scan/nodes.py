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

from ai_backend.domain.guardrails.output_checks import strip_buy_sell
from ai_backend.domain.agents.scan.state import ScanHierarchicalState, main_item
from ai_backend.infra.llm.params import DETERMINISTIC
from ai_backend.infra.llm.structured import call_llm_structured
from ai_backend.infra.monitoring.tracing import trace_step
from ai_backend.infra.prompts import registry
from common.domain.entities import AlertStatus, FinalAlert
from common.transport.schemas import ClassifierOutput, SynthesisAlertOutput
from ai_backend.shared.settings import ai_settings

DEFAULT_THRESHOLD_PCT = 3.0


def resolve_scan_threshold(sym: str, user_id: str | None, deps: dict) -> float:
    """deps.threshold_pct → watchlist → config mặc định (chỉ dùng khi bootstrap task / response)."""
    threshold = deps["threshold_pct"]
    if threshold is None:
        store = deps["watchlist_store"]
        if store is not None:
            try:
                item = store.get(user_id or "default", sym)
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


async def event_classifier_node(state: ScanHierarchicalState, config: RunnableConfig) -> dict:
    """LLM phân loại biến động của mã chính (giá + tin, ngưỡng) bình thường / bất thường → event_routing."""
    price = main_item(state["prices"], state)
    news = main_item(state["news"], state)
    titles = "; ".join(i.title for i in (news.items if news else [])[:10]) or "(không có tin)"
    prompt = registry().render(
        "event_classification",
        version="production",
        symbol=state["symbols"][0],
        latest_close=f"{price.latest_close}" if price else "N/A",
        change_pct=f"{price.change_pct}" if price else "N/A",
        threshold_pct=f"{_threshold_from_context(state)}",
        news_titles=titles,
    )
    with trace_step(get_runtime().context["trace_span"], "event_classifier", input=state["symbols"][0]) as box:
        out = call_llm_structured([{"role": "user", "content": prompt}], ClassifierOutput, params=DETERMINISTIC)
        routing = out.to_routing_decision()
        box["output"] = {"route": routing.route.value, "reason": routing.reason}
    return {"event_routing": routing, "result": f"{routing.route.value} — {routing.reason}"}


async def synthesis_node(state: ScanHierarchicalState, config: RunnableConfig) -> dict:
    """LLM soạn cảnh báo cho mã chính từ đánh giá eval_agent → gửi ngay qua notifier (không HITL) + ghi ``alert`` trên state."""
    sym = state["symbols"][0]
    severity = state["eval_result"].severity
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
    with trace_step(get_runtime().context["trace_span"], "synthesis_agent", input=sym) as box:
        out = call_llm_structured([{"role": "user", "content": prompt}], SynthesisAlertOutput, params=DETERMINISTIC)
        alert = FinalAlert(
            id=str(uuid.uuid4()),
            symbol=sym,
            title=out.title,
            body=strip_buy_sell(out.body),
            severity=severity,
            status=AlertStatus.DRAFT,
            metadata={"user_id": state["user_id"] or "default"},
        )
        get_runtime().context["notifier"].send(alert)  # cảnh báo phải tới ngay — ConsoleNotifier đặt status=SENT
        box["output"] = {"alert_id": alert.id, "title": alert.title, "status": alert.status.value}
    return {"alert": alert, "result": f"đã gửi cảnh báo '{alert.title}'"}
