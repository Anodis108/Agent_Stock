"""Luồng hỏi-đáp: Rewrite → Supervisor → workers → AnswerComposer → Guardrail.

Không qua HITL (không Notifier / không pending_approval).
"""

from __future__ import annotations

import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any

from src.portfolio_watch.domain.agents.answer_composer import (
    AnswerComposeResult,
    AnswerDraftBrain,
    run_answer_composer,
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
    has_change_pct_evidence,
    prices_have_change_pct_evidence,
    run_price_agent,
)
from src.portfolio_watch.domain.agents.supervisor import (
    RewriteBrain,
    RewrittenQuestion,
    SupervisorBrain,
    rewrite_question,
    route_question,
)
from src.portfolio_watch.domain.entities import RoutingDecision
from src.portfolio_watch.domain.ports import (
    MemoryStore,
    NewsSource,
    PriceHistoryStore,
    PriceSource,
)
from src.portfolio_watch.infra.monitoring.tracing import agent_span, trace_request
from src.portfolio_watch.shared.logging import get_logger

_logger = get_logger(__name__)


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
    hitl_used: bool = False
    pending_approvals_created: int = 0
    error: str | None = None
    # Contract UI/Backend: [{id, name, status, detail?}]
    steps: list[dict] = field(default_factory=list)


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
    """Danh sách bước tối thiểu cho timeline UI / trajectory."""
    steps: list[dict] = []
    n = 1

    def add(name: str, status: str, detail: str | None = None) -> None:
        nonlocal n
        steps.append(
            {"id": str(n), "name": name, "status": status, "detail": detail}
        )
        n += 1

    add(
        "rewrite_question",
        "done",
        rewritten.rewritten or rewritten.original or None,
    )
    add(
        "supervisor",
        "done",
        f"{getattr(routing.route, 'value', routing.route)}: "
        f"{list(routing.agents_to_call or [])}"
        + (f" — {routing.reason}" if routing.reason else ""),
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
        )
    if news is not None:
        add(
            "news_agent",
            "error" if news.error else "done",
            f"items={len(news.items or [])}"
            + (f" err={news.error}" if news.error else ""),
        )
    if eval_result is not None:
        add("eval_agent", "done", str(eval_result.severity))
    compose_status = "error" if error else "done"
    if compose is not None and getattr(compose, "guardrail_violations", None):
        detail = answer[:200] if answer else None
        if compose.guardrail_violations:
            detail = (
                f"guardrail={compose.guardrail_violations!r}; {detail or ''}"
            ).strip()
        add("answer_composer", compose_status, detail)
    else:
        add("answer_composer", compose_status, (answer or error or "")[:200] or None)
    return steps


def _with_steps(result: AnswerQuestionResult) -> AnswerQuestionResult:
    result.steps = build_chat_steps(
        rewritten=result.rewritten,
        routing=result.routing,
        price=result.price,
        news=result.news,
        eval_result=result.eval_result,
        answer=result.answer,
        error=result.error,
        compose=result.compose,
    )
    return result


def answer_question(
    question: str,
    *,
    price_source: PriceSource,
    news_source: NewsSource,
    history_store: PriceHistoryStore,
    memory_store: MemoryStore,
    user_id: str = "default",
    request_id: str | None = None,
    rewrite_brain: RewriteBrain | None = None,
    supervisor_brain: SupervisorBrain | None = None,
    news_brain: NewsAgentBrain | None = None,
    eval_brain: EvalAgentBrain | None = None,
    answer_brain: AnswerDraftBrain | None = None,
    news_days: int | None = 7,
) -> AnswerQuestionResult:
    q = (question or "").strip()
    if not q:
        empty = RewrittenQuestion(
            original="", rewritten="", symbol=None, intent="price_lookup"
        )
        routing = RoutingDecision(
            route="price_lookup", reason="câu hỏi rỗng", agents_to_call=[]
        )
        return _with_steps(
            AnswerQuestionResult(
                question="",
                rewritten=empty,
                routing=routing,
                answer="Câu hỏi rỗng — vui lòng nhập nội dung.",
                error="câu hỏi rỗng",
                hitl_used=False,
                pending_approvals_created=0,
            )
        )

    rid = (request_id or "").strip() or None
    turn = rid or str(uuid.uuid4())
    meta: dict[str, Any] = {"turn": turn, "user_id": user_id, "kind": "chat"}
    if rid:
        meta["request_id"] = rid
    with trace_request(
        "chat",
        q,
        metadata=meta,
    ) as root:
        result = _answer_question_traced(
            q,
            turn=turn,
            price_source=price_source,
            news_source=news_source,
            history_store=history_store,
            memory_store=memory_store,
            user_id=user_id,
            rewrite_brain=rewrite_brain,
            supervisor_brain=supervisor_brain,
            news_brain=news_brain,
            eval_brain=eval_brain,
            answer_brain=answer_brain,
            news_days=news_days,
        )
        root["output"] = result.answer
        return result


def _answer_question_traced(
    q: str,
    *,
    turn: str,
    price_source: PriceSource,
    news_source: NewsSource,
    history_store: PriceHistoryStore,
    memory_store: MemoryStore,
    user_id: str,
    rewrite_brain: RewriteBrain | None,
    supervisor_brain: SupervisorBrain | None,
    news_brain: NewsAgentBrain | None,
    eval_brain: EvalAgentBrain | None,
    answer_brain: AnswerDraftBrain | None,
    news_days: int | None,
) -> AnswerQuestionResult:
    conversation = memory_store.list_conversation(user_id, limit=20)
    alerts_before = len(memory_store.list_alert_events(user_id, limit=1000))

    with agent_span(turn, "rewrite_question", input=q) as box:
        rewritten = rewrite_question(q, conversation, brain=rewrite_brain)
        box["output"] = {
            "rewritten": rewritten.rewritten,
            "symbol": rewritten.symbol,
            "symbols": list(rewritten.symbols or []),
        }

    with agent_span(turn, "supervisor", input=rewritten.rewritten) as box:
        routing = route_question(rewritten, brain=supervisor_brain)
        box["output"] = {
            "route": str(getattr(routing.route, "value", routing.route)),
            "agents_to_call": list(routing.agents_to_call or []),
            "reason": routing.reason,
        }

    agents = [a.lower() for a in (routing.agents_to_call or [])]

    price: PriceAgentResult | None = None
    news: NewsAgentResult | None = None
    eval_result: EvalAgentResult | None = None
    prices: list[PriceAgentResult] = []
    news_list: list[NewsAgentResult] = []
    symbols = list(rewritten.symbols) if rewritten.symbols else []
    if not symbols and rewritten.symbol:
        symbols = [rewritten.symbol]
    symbol = rewritten.symbol or (symbols[0] if symbols else None)

    def _hitl_stats() -> tuple[bool, int]:
        events = memory_store.list_alert_events(user_id, limit=1000)
        new_events = events[alerts_before:]
        pending = sum(
            1
            for e in new_events
            if e.get("kind") == "pending_approval" or e.get("gate") in ("gate1", "gate2")
        )
        return pending > 0, pending

    try:
        need_price = "price" in agents
        need_news = "news" in agents
        need_eval = "eval" in agents

        if not symbols and (need_price or need_news or need_eval):
            _logger.info("answer_question: không suy ra được symbol từ '%s'", q)

        def _fetch_one(sym: str) -> tuple[PriceAgentResult | None, NewsAgentResult | None]:
            p_res: PriceAgentResult | None = None
            n_res: NewsAgentResult | None = None
            if need_price and need_news and len(symbols) == 1:
                with ThreadPoolExecutor(max_workers=2) as pool:
                    fut_p = pool.submit(run_price_agent, sym, price_source)
                    fut_n = pool.submit(
                        run_news_agent,
                        sym,
                        news_source,
                        news_brain or default_news_brain(),
                        days=news_days,
                    )
                    p_res = fut_p.result()
                    n_res = fut_n.result()
            else:
                if need_price:
                    p_res = run_price_agent(sym, price_source)
                if need_news:
                    n_res = run_news_agent(
                        sym,
                        news_source,
                        news_brain or default_news_brain(),
                        days=news_days,
                    )
            return p_res, n_res

        if symbols and (need_price or need_news):
            with agent_span(
                turn,
                "price_news_fetch",
                input={"symbols": symbols, "need_price": need_price, "need_news": need_news},
            ) as box:
                if len(symbols) == 1:
                    price, news = _fetch_one(symbols[0])
                    if price is not None:
                        prices = [price]
                    if news is not None:
                        news_list = [news]
                else:
                    with ThreadPoolExecutor(max_workers=min(4, len(symbols))) as pool:
                        futs = {pool.submit(_fetch_one, sym): sym for sym in symbols}
                        by_sym: dict[str, tuple] = {}
                        for fut in futs:
                            by_sym[futs[fut]] = fut.result()
                    for sym in symbols:
                        p_res, n_res = by_sym[sym]
                        if p_res is not None:
                            prices.append(p_res)
                        if n_res is not None:
                            news_list.append(n_res)
                    price = prices[0] if prices else None
                    news = news_list[0] if news_list else None
                box["output"] = {
                    "prices": len(prices),
                    "news": len(news_list),
                }

        if need_eval and symbol:
            have = {p.symbol.upper() for p in prices if p.symbol}
            for sym in symbols:
                if sym.upper() not in have:
                    p_res = run_price_agent(sym, price_source)
                    prices.append(p_res)
                    if sym.upper() == (symbol or "").upper():
                        price = p_res
            if price is None and prices:
                price = next(
                    (p for p in prices if p.symbol.upper() == symbol.upper()),
                    prices[0],
                )
            if news is None:
                news = run_news_agent(
                    symbol,
                    news_source,
                    news_brain or default_news_brain(),
                    days=news_days,
                )
                if news is not None and not news_list:
                    news_list = [news]
            if news is None:
                news = NewsAgentResult(symbol=symbol or "", items=[], tool_calls=0)
            ready = prices_have_change_pct_evidence(prices, symbols) or (
                len(symbols) <= 1 and has_change_pct_evidence(price)
            )
            if not ready:
                _logger.info(
                    "skip eval_agent: thiếu evidence giá change_pct symbols=%s",
                    symbols,
                )
                eval_result = None
            else:
                with agent_span(turn, "eval_agent", input=symbol) as box:
                    eval_result = run_eval_agent(
                        price, news, history_store, brain=eval_brain
                    )
                    box["output"] = str(eval_result.severity)

        with agent_span(turn, "answer_composer", input=symbol) as box:
            compose = run_answer_composer(
                question=rewritten.rewritten or q,
                symbol=symbol,
                price=price,
                news=news,
                eval_result=eval_result,
                memory_store=memory_store,
                user_id=user_id,
                brain=answer_brain,
                prices=prices or None,
                news_list=news_list or None,
            )
            box["output"] = (compose.answer or "")[:500]

        memory_store.append_conversation(user_id, "user", q)
        memory_store.append_conversation(user_id, "assistant", compose.answer)

        hitl_used, pending_n = _hitl_stats()
        result = AnswerQuestionResult(
            question=q,
            rewritten=rewritten,
            routing=routing,
            answer=compose.answer,
            price=price,
            news=news,
            eval_result=eval_result,
            compose=compose,
            hitl_used=hitl_used,
            pending_approvals_created=pending_n,
        )
        _logger.info(
            "answer_question symbol=%s agents=%s hitl=%s",
            symbol,
            agents,
            hitl_used,
        )
        return _with_steps(result)
    except Exception as exc:  # noqa: BLE001
        err = f"không trả lời được: {exc}"
        memory_store.append_conversation(user_id, "user", q)
        memory_store.append_conversation(user_id, "assistant", err)
        hitl_used, pending_n = _hitl_stats()
        return _with_steps(
            AnswerQuestionResult(
                question=q,
                rewritten=rewritten,
                routing=routing,
                answer=err,
                price=price,
                news=news,
                eval_result=eval_result,
                hitl_used=hitl_used,
                pending_approvals_created=pending_n,
                error=err,
            )
        )
