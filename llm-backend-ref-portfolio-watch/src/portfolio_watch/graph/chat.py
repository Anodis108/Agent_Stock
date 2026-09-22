"""LangGraph chat — rewrite → supervisor → workers → answer_composer."""

from __future__ import annotations

import contextvars
import uuid
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from typing import Any

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph

from src.portfolio_watch.application.answer_question import (
    AnswerQuestionResult,
    build_chat_steps,
)
from src.portfolio_watch.agents.answer_composer import (
    AnswerDraftBrain,
    run_answer_composer,
)
from src.portfolio_watch.agents.diagram_agent import run_diagram_agent
from src.portfolio_watch.agents.eval_agent import EvalAgentBrain, run_eval_agent
from src.portfolio_watch.agents.news_agent import (
    NewsAgentBrain,
    NewsAgentResult,
    default_news_brain,
    run_news_agent,
)
from src.portfolio_watch.agents.price_agent import (
    PriceAgentResult,
    has_change_pct_evidence,
    prices_have_change_pct_evidence,
    run_price_agent,
)
from src.portfolio_watch.agents.supervisor_agent import (
    RewriteBrain,
    SupervisorBrain,
    recall_memory,
    rewrite_question,
    route_question,
    store_memory,
)
from src.portfolio_watch.domain.entities import RoutingDecision
from src.portfolio_watch.domain.ports import (
    MemoryStore,
    NewsSource,
    PriceHistoryStore,
    PriceSource,
)
from src.portfolio_watch.graph.state import ChatState
from src.portfolio_watch.infra.monitoring.tracing import agent_span
from src.portfolio_watch.infra.storage.memory_store import filter_conversation_history
from src.portfolio_watch.shared.logging import get_logger
from src.portfolio_watch.shared.settings import settings

_logger = get_logger(__name__)
_chat_deps: contextvars.ContextVar[dict[str, Any]] = contextvars.ContextVar(
    "_chat_deps", default={}
)


def _cfg(_config: RunnableConfig) -> dict[str, Any]:
    return _chat_deps.get()


def _node_rewrite(state: ChatState, config: RunnableConfig) -> dict:
    cfg = _cfg(config)
    turn = state.get("turn") or ""
    with agent_span(turn, "rewrite_question", input=state.get("question", "")) as box:
        rewritten = rewrite_question(
            state["question"],
            state.get("conversation") or [],
            brain=cfg.get("rewrite_brain"),
            turn=turn,
            memories=state.get("memories") or [],
        )
        box["output"] = {
            "rewritten": rewritten.rewritten,
            "symbol": rewritten.symbol,
            "symbols": list(rewritten.symbols or []),
        }
    symbols = list(rewritten.symbols) if rewritten.symbols else []
    if not symbols and rewritten.symbol:
        symbols = [rewritten.symbol]
    return {
        "rewritten": rewritten,
        "symbol": rewritten.symbol or (symbols[0] if symbols else None),
        "symbols": symbols,
    }


def _node_supervisor(state: ChatState, config: RunnableConfig) -> dict:
    cfg = _cfg(config)
    turn = state.get("turn") or ""
    rewritten = state["rewritten"]
    with agent_span(turn, "supervisor", input=rewritten.rewritten) as box:
        routing = route_question(
            rewritten, brain=cfg.get("supervisor_brain"), turn=turn
        )
        box["output"] = {
            "route": str(getattr(routing.route, "value", routing.route)),
            "agents_to_call": list(routing.agents_to_call or []),
            "reason": routing.reason,
        }
    return {"routing": routing}


def _node_workers(state: ChatState, config: RunnableConfig) -> dict:
    cfg = _cfg(config)
    turn = state.get("turn") or ""
    routing = state["routing"]
    agents = [a.lower() for a in (routing.agents_to_call or [])]
    symbols = list(state.get("symbols") or [])
    symbol = state.get("symbol")
    price_source: PriceSource = cfg["price_source"]
    news_source: NewsSource = cfg["news_source"]
    history_store: PriceHistoryStore = cfg["history_store"]
    news_brain: NewsAgentBrain | None = cfg.get("news_brain")
    eval_brain: EvalAgentBrain | None = cfg.get("eval_brain")
    news_days: int | None = cfg.get("news_days", 7)

    need_price = "price" in agents
    need_news = "news" in agents
    need_eval = "eval" in agents
    price: PriceAgentResult | None = None
    news: NewsAgentResult | None = None
    eval_result = None
    prices: list[PriceAgentResult] = []
    news_list: list[NewsAgentResult] = []

    def _fetch_price_one(sym: str) -> PriceAgentResult:
        with agent_span(turn, "price_agent", input=sym) as box:
            p = run_price_agent(sym, price_source, turn)
            box["output"] = {
                "symbol": sym,
                "latest_close": p.latest_close,
                "change_pct": p.change_pct,
                "error": p.error,
            }
            return p

    def _fetch_news_one(sym: str) -> NewsAgentResult:
        with agent_span(turn, "news_agent", input=sym) as box:
            n = run_news_agent(
                sym,
                news_source,
                news_brain or default_news_brain(),
                days=news_days,
                turn=turn,
            )
            box["output"] = {
                "symbol": sym,
                "items": len(n.items or []),
                "error": n.error,
            }
            return n

    def _fetch_one(sym: str) -> tuple[PriceAgentResult | None, NewsAgentResult | None]:
        p_res: PriceAgentResult | None = None
        n_res: NewsAgentResult | None = None
        if need_price and need_news:
            with ThreadPoolExecutor(max_workers=2) as pool:
                fut_p = pool.submit(_fetch_price_one, sym)
                fut_n = pool.submit(_fetch_news_one, sym)
                p_res = fut_p.result()
                n_res = fut_n.result()
        else:
            if need_price:
                p_res = _fetch_price_one(sym)
            if need_news:
                n_res = _fetch_news_one(sym)
        return p_res, n_res

    if symbols and (need_price or need_news):
        if len(symbols) == 1:
            price, news = _fetch_one(symbols[0])
            if price is not None:
                prices = [price]
            if news is not None:
                news_list = [news]
        else:
            with ThreadPoolExecutor(max_workers=min(4, len(symbols))) as pool:
                futs = {pool.submit(_fetch_one, sym): sym for sym in symbols}
                by_sym = {futs[fut]: fut.result() for fut in futs}
            for sym in symbols:
                p_res, n_res = by_sym[sym]
                if p_res is not None:
                    prices.append(p_res)
                if n_res is not None:
                    news_list.append(n_res)
            price = prices[0] if prices else None
            news = news_list[0] if news_list else None

    if need_eval and symbol:
        have = {p.symbol.upper() for p in prices if p.symbol}
        for sym in symbols:
            if sym.upper() not in have:
                p_res = _fetch_price_one(sym)
                prices.append(p_res)
                if sym.upper() == (symbol or "").upper():
                    price = p_res
        if price is None and prices:
            price = next(
                (p for p in prices if p.symbol.upper() == symbol.upper()),
                prices[0],
            )
        if news is None:
            news = _fetch_news_one(symbol)
            if news is not None and not news_list:
                news_list = [news]
        if news is None:
            news = NewsAgentResult(symbol=symbol or "", items=[], tool_calls=0)
        ready = prices_have_change_pct_evidence(prices, symbols) or (
            len(symbols) <= 1 and has_change_pct_evidence(price)
        )
        if ready:
            with agent_span(turn, "eval_agent", input=symbol) as box:
                eval_result = run_eval_agent(
                    price, news, history_store, brain=eval_brain, turn=turn
                )
                box["output"] = {
                    "symbol": symbol,
                    "severity": str(eval_result.severity),
                    "confidence": eval_result.severity.confidence,
                }

    return {
        "price": price,
        "news": news,
        "prices": prices,
        "news_list": news_list,
        "eval_result": eval_result,
    }


def _node_answer_composer(state: ChatState, config: RunnableConfig) -> dict:
    cfg = _cfg(config)
    turn = state.get("turn") or ""
    symbol = state.get("symbol")
    input_sym = symbol or state.get("question", "")
    with agent_span(turn, "answer_composer", input=input_sym) as box:
        compose = run_answer_composer(
            question=state["rewritten"].rewritten or state["question"],
            symbol=symbol,
            price=state.get("price"),
            news=state.get("news"),
            eval_result=state.get("eval_result"),
            memory_store=cfg["memory_store"],
            user_id=state.get("user_id") or "default",
            brain=cfg.get("answer_brain"),
            prices=state.get("prices") or None,
            news_list=state.get("news_list") or None,
            turn=turn,
        )
        box["output"] = (compose.answer or "")[:500]
    return {"compose": compose, "answer": compose.answer}


def _node_diagram_agent(state: ChatState, config: RunnableConfig) -> dict:
    cfg = _cfg(config)
    turn = state.get("turn") or ""
    symbol = state.get("symbol")
    with agent_span(turn, "diagram_agent", input=symbol or state.get("question", "")) as box:
        result = run_diagram_agent(
            symbol,
            turn=turn,
            question=state.get("question") or "",
            brain=cfg.get("diagram_brain")
        )
        box["output"] = result.placeholder
    from src.portfolio_watch.agents.answer_composer import AnswerComposeResult
    compose = AnswerComposeResult(answer=result.placeholder, model="stub", draft_attempts=1, guardrail_violations=[], evidence=[], hitl_used=False)
    return {"diagram_result": result, "answer": result.placeholder, "compose": compose}

def route_from_supervisor(state: ChatState) -> str:
    route = getattr(state["routing"].route, "value", state["routing"].route)
    if str(route) == "diagram" or "diagram" in (state["routing"].agents_to_call or []):
        return "diagram_agent"
    return "workers"

def build_chat_graph() -> StateGraph:
    graph = StateGraph(ChatState)
    graph.add_node("rewrite_question", _node_rewrite)
    graph.add_node("supervisor", _node_supervisor)
    graph.add_node("diagram_agent", _node_diagram_agent)
    graph.add_node("workers", _node_workers)
    graph.add_node("answer_composer", _node_answer_composer)
    graph.add_edge(START, "rewrite_question")
    graph.add_edge("rewrite_question", "supervisor")
    graph.add_conditional_edges("supervisor", route_from_supervisor, {"diagram_agent": "diagram_agent", "workers": "workers"})
    graph.add_edge("diagram_agent", END)
    graph.add_edge("workers", "answer_composer")
    graph.add_edge("answer_composer", END)
    return graph


@lru_cache(maxsize=1)
def compile_chat_graph():
    return build_chat_graph().compile()


def run_chat_graph(
    question: str,
    *,
    price_source: PriceSource,
    news_source: NewsSource,
    history_store: PriceHistoryStore,
    memory_store: MemoryStore,
    user_id: str | None = "default",
    request_id: str | None = None,
    turn: str = "",
    rewrite_brain: RewriteBrain | None = None,
    supervisor_brain: SupervisorBrain | None = None,
    news_brain: NewsAgentBrain | None = None,
    eval_brain: EvalAgentBrain | None = None,
    answer_brain: AnswerDraftBrain | None = None,
    diagram_brain: Any | None = None,
    news_days: int | None = 7,
    limit: int | None = None,
    ttl_minutes: int | float | None = None,
    extract_fn: Any | None = None,
) -> AnswerQuestionResult:
    """Invoke compiled chat graph — trả cùng contract `answer_question`."""
    q = (question or "").strip()
    effective_limit = (
        limit if limit is not None else settings.memory_short_term_window
    )
    effective_ttl = (
        ttl_minutes
        if ttl_minutes is not None
        else settings.memory_short_term_ttl_minutes
    )
    effective_user_id = str(user_id or "").strip() if user_id is not None else ""
    short_term_user_id = user_id if user_id is not None else "default"

    try:
        conversation = memory_store.list_conversation(
            short_term_user_id, limit=effective_limit, ttl_minutes=effective_ttl
        )
    except TypeError:
        conversation = memory_store.list_conversation(
            short_term_user_id, limit=effective_limit
        )
    conversation = filter_conversation_history(
        conversation,
        limit=effective_limit,
        ttl_minutes=effective_ttl,
    )

    turn_id = (turn or "").strip() or (request_id or "").strip() or str(uuid.uuid4())

    # Long-term recall (pattern agent_pr: early in chat turn)
    # Empty / None / blank user_id -> skip long-term entirely
    recalled_memories: list[str] = []
    if effective_user_id:
        recall_res = recall_memory(
            {"user_id": effective_user_id, "question": q, "turn": turn_id}
        )
        recalled_memories = recall_res.get("memories") or []

    if not q:
        empty_rw = rewrite_question(
            "", conversation, brain=rewrite_brain, memories=recalled_memories
        )
        routing = RoutingDecision(
            route="price_lookup", reason="câu hỏi rỗng", agents_to_call=[]
        )
        return AnswerQuestionResult(
            question="",
            rewritten=empty_rw,
            routing=routing,
            answer="Câu hỏi rỗng — vui lòng nhập nội dung.",
            error="câu hỏi rỗng",
            steps=build_chat_steps(
                rewritten=empty_rw,
                routing=routing,
                error="câu hỏi rỗng",
            ),
            memories=recalled_memories,
        )

    deps = {
        "price_source": price_source,
        "news_source": news_source,
        "history_store": history_store,
        "memory_store": memory_store,
        "rewrite_brain": rewrite_brain,
        "supervisor_brain": supervisor_brain,
        "news_brain": news_brain,
        "eval_brain": eval_brain,
        "answer_brain": answer_brain,
        "diagram_brain": diagram_brain,
        "news_days": news_days,
    }
    token = _chat_deps.set(deps)
    try:
        final = {
            "question": q,
            "user_id": user_id,
            "turn": turn_id,
            "conversation": conversation,
            "memories": recalled_memories,
        }
        chunks = []
        for chunk in compile_chat_graph().stream(
            final,
            config=RunnableConfig(recursion_limit=25),
            stream_mode="updates",
        ):
            chunks.append(chunk)
            for node, values in chunk.items():
                final.update(values)
    finally:
        _chat_deps.reset(token)

    compose = final.get("compose")
    answer_text = final.get("answer") or ""

    # Short-term append
    memory_store.append_conversation(short_term_user_id, "user", q)
    memory_store.append_conversation(short_term_user_id, "assistant", answer_text)

    # Long-term store (pattern agent_pr: late in chat turn, after answer)
    # Empty / None / blank user_id -> skip long-term entirely
    if effective_user_id:
        store_memory(
            {
                "user_id": effective_user_id,
                "question": q,
                "answer": answer_text,
                "symbols": final.get("symbols") or [],
                "rewritten_question": getattr(final.get("rewritten"), "rewritten", ""),
                "turn": turn_id,
            },
            extract_fn=extract_fn,
        )

    result = AnswerQuestionResult(
        question=q,
        rewritten=final["rewritten"],
        routing=final["routing"],
        answer=answer_text,
        price=final.get("price"),
        news=final.get("news"),
        eval_result=final.get("eval_result"),
        compose=compose,
        diagram_result=final.get("diagram_result"),
        error=final.get("error"),
        memories=recalled_memories,
    )

    from src.portfolio_watch.graph.steps import build_steps_from_chunks
    result.steps = build_steps_from_chunks(chunks, final_error=result.error)

    _logger.info(
        "run_chat_graph symbol=%s agents=%s",
        result.rewritten.symbol,
        result.routing.agents_to_call,
    )
    return result
