"""Luồng hỏi-đáp: Rewrite → Supervisor → workers → AnswerComposer → Guardrail.

Không qua HITL (không Notifier / không pending_approval).
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

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


def answer_question(
    question: str,
    *,
    price_source: PriceSource,
    news_source: NewsSource,
    history_store: PriceHistoryStore,
    memory_store: MemoryStore,
    user_id: str = "default",
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
        return AnswerQuestionResult(
            question="",
            rewritten=empty,
            routing=RoutingDecision(
                route="price_lookup", reason="câu hỏi rỗng", agents_to_call=[]
            ),
            answer="Câu hỏi rỗng — vui lòng nhập nội dung.",
            error="câu hỏi rỗng",
            hitl_used=False,
            pending_approvals_created=0,
        )

    conversation = memory_store.list_conversation(user_id, limit=20)
    alerts_before = len(memory_store.list_alert_events(user_id, limit=1000))
    rewritten = rewrite_question(q, conversation, brain=rewrite_brain)
    routing = route_question(rewritten, brain=supervisor_brain)
    agents = [a.lower() for a in (routing.agents_to_call or [])]

    price: PriceAgentResult | None = None
    news: NewsAgentResult | None = None
    eval_result: EvalAgentResult | None = None
    symbol = rewritten.symbol

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

        if symbol is None and (need_price or need_news or need_eval):
            # Vẫn cố trả lời; composer sẽ nói thiếu mã
            _logger.info("answer_question: không suy ra được symbol từ '%s'", q)

        if need_price and need_news and symbol:
            with ThreadPoolExecutor(max_workers=2) as pool:
                fut_p = pool.submit(run_price_agent, symbol, price_source)
                fut_n = pool.submit(
                    run_news_agent,
                    symbol,
                    news_source,
                    news_brain or default_news_brain(),
                    days=news_days,
                )
                price = fut_p.result()
                news = fut_n.result()
        elif need_price and symbol:
            price = run_price_agent(symbol, price_source)
        elif need_news and symbol:
            news = run_news_agent(
                symbol,
                news_source,
                news_brain or default_news_brain(),
                days=news_days,
            )

        if need_eval and symbol:
            if price is None:
                price = run_price_agent(symbol, price_source)
            if news is None:
                news = run_news_agent(
                    symbol,
                    news_source,
                    news_brain or default_news_brain(),
                    days=news_days,
                )
            eval_result = run_eval_agent(
                price, news, history_store, brain=eval_brain
            )

        compose = run_answer_composer(
            question=rewritten.rewritten or q,
            symbol=symbol,
            price=price,
            news=news,
            eval_result=eval_result,
            memory_store=memory_store,
            user_id=user_id,
            brain=answer_brain,
        )

        # Lưu hội thoại — không tạo pending / không gọi Notifier
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
        return result
    except Exception as exc:  # noqa: BLE001
        err = f"không trả lời được: {exc}"
        memory_store.append_conversation(user_id, "user", q)
        memory_store.append_conversation(user_id, "assistant", err)
        hitl_used, pending_n = _hitl_stats()
        return AnswerQuestionResult(
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
