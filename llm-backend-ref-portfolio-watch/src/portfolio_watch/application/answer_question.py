"""Luồng hỏi-đáp — wrapper gọi LangGraph chat; giữ contract API/eval."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from src.portfolio_watch.agents.answer_composer import (
    AnswerComposeResult,
    AnswerDraftBrain,
)
from src.portfolio_watch.agents.eval_agent import EvalAgentBrain, EvalAgentResult
from src.portfolio_watch.agents.news_agent import NewsAgentBrain, NewsAgentResult
from src.portfolio_watch.agents.price_agent import PriceAgentResult
from src.portfolio_watch.agents.supervisor_agent import (
    RewriteBrain,
    RewrittenQuestion,
    SupervisorBrain,
)
from src.portfolio_watch.domain.entities import RoutingDecision
from src.portfolio_watch.domain.ports import (
    MemoryStore,
    NewsSource,
    PriceHistoryStore,
    PriceSource,
)
from src.portfolio_watch.infra.monitoring.tracing import trace_request


@dataclass(slots=True)
class AnswerQuestionResult:
    question: str
    rewritten: RewrittenQuestion
    routing: RoutingDecision
    answer: str
    price: PriceAgentResult | None = None
    news: NewsAgentResult | None = None
    eval_result: EvalAgentResult | None = None
    compose: AnswerComposeResult | None = None
    diagram_result: Any | None = None
    hitl_used: bool = False
    pending_approvals_created: int = 0
    error: str | None = None
    steps: list[dict] = field(default_factory=list)
    memories: list[str] = field(default_factory=list)


def build_chat_steps(
    *,
    rewritten: RewrittenQuestion,
    routing: RoutingDecision,
    price: PriceAgentResult | None = None,
    news: NewsAgentResult | None = None,
    eval_result: EvalAgentResult | None = None,
    answer: str = "",
    error: str | None = None,
    compose: AnswerComposeResult | None = None,
) -> list[dict]:
    """Danh sách bước tối thiểu cho timeline UI / trajectory (legacy helper)."""
    steps: list[dict] = []
    n = 1

    def add(
        name: str,
        status: str,
        detail: str | None = None,
        input_data: Any = None,
        output_data: Any = None,
    ) -> None:
        nonlocal n
        s: dict[str, Any] = {
            "id": str(n),
            "name": name,
            "status": status,
        }
        if detail is not None:
            s["detail"] = detail
        if input_data is not None:
            s["input"] = input_data
        if output_data is not None:
            s["output"] = output_data
        steps.append(s)
        n += 1

    add(
        "rewrite_question",
        "done",
        rewritten.rewritten or rewritten.original or None,
        input_data={"question": rewritten.original or ""},
        output_data={
            "rewritten": rewritten.rewritten or "",
            "symbol": rewritten.symbol,
            "symbols": list(rewritten.symbols or []),
        },
    )
    route_str = str(getattr(routing.route, "value", routing.route))
    agents_list = list(routing.agents_to_call or [])
    add(
        "supervisor",
        "done",
        f"{route_str}: {agents_list}"
        + (f" — {routing.reason}" if routing.reason else ""),
        input_data={"question": rewritten.rewritten or rewritten.original or ""},
        output_data={
            "route": route_str,
            "agents": agents_list,
            "reason": routing.reason or "",
        },
    )
    if price is not None:
        add(
            "price_agent",
            "error" if price.error else "done",
            (
                f"{price.symbol} close={price.latest_close} "
                f"chg={price.change_pct}"
                + (f" err={price.error}" if price.error else "")
            ),
            input_data={"symbol": price.symbol},
            output_data={
                "symbol": price.symbol,
                "latest_close": price.latest_close,
                "change_pct": price.change_pct,
                "error": price.error,
            },
        )
    if news is not None:
        add(
            "news_agent",
            "error" if news.error else "done",
            f"items={len(news.items or [])}"
            + (f" err={news.error}" if news.error else ""),
            input_data={"symbol": getattr(news, "symbol", "") or (price.symbol if price else "")},
            output_data={
                "symbol": getattr(news, "symbol", "") or (price.symbol if price else ""),
                "items_count": len(news.items or []),
                "error": news.error,
            },
        )
    if eval_result is not None:
        add(
            "eval_agent",
            "done",
            str(eval_result.severity),
            input_data={"symbol": price.symbol if price else ""},
            output_data={
                "severity": str(eval_result.severity),
                "confidence": getattr(eval_result.severity, "confidence", None),
            },
        )
    compose_status = "error" if error else "done"
    in_syms = [price.symbol] if price else ([rewritten.symbol] if rewritten.symbol else [])
    out_compose = {
        "answer": (answer or error or "")[:300],
        "guardrail_violations": getattr(compose, "guardrail_violations", None) if compose else None,
    }
    if compose is not None and getattr(compose, "guardrail_violations", None):
        detail = answer[:200] if answer else None
        if compose.guardrail_violations:
            detail = (
                f"guardrail={compose.guardrail_violations!r}; {detail or ''}"
            ).strip()
        add(
            "answer_composer",
            compose_status,
            detail,
            input_data={"symbols": in_syms},
            output_data=out_compose,
        )
    else:
        add(
            "answer_composer",
            compose_status,
            (answer or error or "")[:200] or None,
            input_data={"symbols": in_syms},
            output_data=out_compose,
        )
    return steps


def answer_question(
    question: str,
    *,
    price_source: PriceSource,
    news_source: NewsSource,
    history_store: PriceHistoryStore,
    memory_store: MemoryStore,
    user_id: str | None = "default",
    request_id: str | None = None,
    rewrite_brain: RewriteBrain | None = None,
    supervisor_brain: SupervisorBrain | None = None,
    news_brain: NewsAgentBrain | None = None,
    eval_brain: EvalAgentBrain | None = None,
    answer_brain: AnswerDraftBrain | None = None,
    news_days: int | None = 7,
    limit: int | None = None,
    ttl_minutes: int | float | None = None,
) -> AnswerQuestionResult:
    q = (question or "").strip()
    rid = (request_id or "").strip() or None
    turn = rid or str(uuid.uuid4())
    meta: dict[str, Any] = {"turn": turn, "user_id": user_id, "kind": "chat"}
    if rid:
        meta["request_id"] = rid

    alerts_before = len(memory_store.list_alert_events(user_id, limit=1000))

    with trace_request("chat", q, metadata=meta) as root:
        from src.portfolio_watch.graph.chat import run_chat_graph

        result = run_chat_graph(
            question=q,
            price_source=price_source,
            news_source=news_source,
            history_store=history_store,
            memory_store=memory_store,
            user_id=user_id,
            request_id=request_id,
            turn=turn,
            rewrite_brain=rewrite_brain,
            supervisor_brain=supervisor_brain,
            news_brain=news_brain,
            eval_brain=eval_brain,
            answer_brain=answer_brain,
            news_days=news_days,
            limit=limit,
            ttl_minutes=ttl_minutes,
        )

        events = memory_store.list_alert_events(user_id, limit=1000)
        new_events = events[alerts_before:]
        pending = sum(
            1
            for e in new_events
            if e.get("kind") == "pending_approval"
            or e.get("gate") in ("gate1", "gate2")
        )
        result.hitl_used = pending > 0
        result.pending_approvals_created = pending

        root["output"] = result.answer
        return result
