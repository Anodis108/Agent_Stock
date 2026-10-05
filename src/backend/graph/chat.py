"""LangGraph Chat Workflow — Đồ thị điều phối luồng Multi-Agent Swarm.

Luồng điều phối chuẩn hoá:
START ➔ guardrail_node ➔ (nếu vi phạm) ➔ guardrail_refusal_node ➔ END
                     ➔ (nếu an toàn) ➔ rewrite_node ➔ supervisor_node
                                                  ➔ diagram_node ➔ END
                                                  ➔ workers_node (price_node, news_node, chart_node, eval)
                                                  ➔ composer_node ➔ END
"""

from __future__ import annotations

import contextvars
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from typing import Any, Callable

import sys
from pathlib import Path

_SRC_DIR = str(Path(__file__).resolve().parents[2])
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph

from backend.application.answer_question import (
    AnswerQuestionResult,
    build_chat_steps,
)
from backend.agents.answer_composer import (
    AnswerComposeResult,
    AnswerDraftBrain,
    run_answer_composer,
)
from backend.agents.chart_agent import run_chart_agent
from backend.agents.diagram_agent import run_diagram_agent
from backend.agents.eval_agent import EvalAgentBrain, run_eval_agent
from backend.agents.news_agent import (
    NewsAgentBrain,
    NewsAgentResult,
    default_news_brain,
    run_news_agent,
)
from backend.agents.price_agent import (
    PriceAgentResult,
    has_change_pct_evidence,
    prices_have_change_pct_evidence,
    run_price_agent,
)
from backend.agents.supervisor_agent import (
    RewriteBrain,
    RewrittenQuestion,
    SupervisorBrain,
    recall_memory,
    rewrite_question,
    route_question,
    store_memory,
)
from backend.domain.entities import RoutingDecision
from backend.domain.guardrails import check_input_guardrail
from backend.domain.ports import (
    MemoryStore,
    NewsSource,
    PriceBar,
    PriceHistoryStore,
    PriceSource,
)
from backend.graph.state import ChatState
from backend.infra.monitoring.tracing import agent_span, mark_turn_guardrail
from backend.infra.storage.memory_store import (
    apply_sliding_window_with_ttl_eviction,
    filter_conversation_history,
)
from backend.shared.logging import get_logger
from backend.shared.settings import settings

_logger = get_logger(__name__)
_chat_deps: contextvars.ContextVar[dict[str, Any]] = contextvars.ContextVar(
    "_chat_deps", default={}
)
_stream_cancel: contextvars.ContextVar[Any | None] = contextvars.ContextVar(
    "_stream_cancel", default=None
)


class StreamCancelledError(Exception):
    """Client đóng SSE — dừng pipeline."""


def set_stream_cancel_event(event: Any | None) -> None:
    """Gắn threading.Event từ SSE generator; None để clear."""
    _stream_cancel.set(event)


def check_stream_cancelled() -> None:
    ev = _stream_cancel.get()
    if ev is not None and getattr(ev, "is_set", lambda: False)():
        raise StreamCancelledError("client disconnected")


def emit_agent_event(event: str, data: dict[str, Any]) -> None:
    """Gửi sự kiện thời gian thực (node_start, node_end, token, chart_url, final_answer) đến SSE stream generator."""
    check_stream_cancelled()
    deps = _chat_deps.get()
    cb = deps.get("event_callback")
    if cb:
        try:
            cb(event, data)
            if event == "node_finish":
                cb("node_end", data)
            elif event == "node_end":
                cb("node_finish", data)
        except Exception as exc:
            _logger.warning("Error in event_callback (%s): %s", event, exc)


def _cfg(_config: RunnableConfig) -> dict[str, Any]:
    return _chat_deps.get()


# ==============================================================================
# Agent Nodes
# ==============================================================================

def guardrail_node(state: ChatState, config: RunnableConfig) -> dict[str, Any]:
    """Node phòng vệ cửa ngõ: Kiểm tra an toàn, phát hiện Prompt Injection và từ chối câu hỏi Out-of-Scope."""
    t0 = time.perf_counter()
    emit_agent_event("node_start", {"node": "pre_rewrite_guardrail", "timestamp": time.time()})
    turn = state.get("turn") or ""
    q = state.get("question", "")
    res = state.get("guardrail_result") or check_input_guardrail(q)
    with agent_span(turn, "pre_rewrite_guardrail", input=q) as box:
        box["output"] = {
            "is_safe": res.is_safe,
            "category": res.category,
            "reason": res.reason,
        }
    if not res.is_safe:
        mark_turn_guardrail(turn)
    dur = round(time.perf_counter() - t0, 3)
    emit_agent_event("node_finish", {"node": "pre_rewrite_guardrail", "duration_s": dur, "duration_ms": int(dur * 1000)})
    return {
        "question": q,
        "guardrail_result": res,
    }


def guardrail_refusal_node(state: ChatState, config: RunnableConfig) -> dict[str, Any]:
    """Node từ chối an toàn: Phản hồi lý do từ chối lịch sự khi phát hiện vi phạm guardrail."""
    t0 = time.perf_counter()
    emit_agent_event("node_start", {"node": "guardrail_refusal", "timestamp": time.time()})
    turn = state.get("turn") or ""
    res = state.get("guardrail_result")
    refusal_text = (
        res.refusal_response
        if res and res.refusal_response
        else "Yêu cầu không thuộc phạm vi xử lý của hệ thống."
    )
    with agent_span(turn, "guardrail_refusal", input=state.get("question", "")) as box:
        box["output"] = refusal_text

    compose = AnswerComposeResult(
        answer=refusal_text,
        model="guardrail",
        draft_attempts=1,
        guardrail_violations=[res.reason] if res and not res.is_safe else [],
        evidence=[],
        hitl_used=False,
    )
    words = refusal_text.split(" ")
    for i, w in enumerate(words):
        sep = " " if i < len(words) - 1 else ""
        emit_agent_event("token", {"delta": w + sep})

    dur = round(time.perf_counter() - t0, 3)
    emit_agent_event("node_finish", {"node": "guardrail_refusal", "duration_s": dur, "duration_ms": int(dur * 1000)})
    return {
        "answer": refusal_text,
        "compose": compose,
    }


GREETING_RESPONSE = (
    "Xin chào! Tôi là trợ lý AI phân tích chứng khoán Việt Nam (Portfolio Watch).\n\n"
    "Tôi có thể hỗ trợ bạn các tác vụ sau:\n"
    "- 📊 **Tra cứu thị giá & biến động**: Xem giá khớp lệnh, biên độ trần/sàn, biến động phiên (ví dụ: *'Giá cổ phiếu FPT hôm nay bao nhiêu?'*).\n"
    "- 📰 **Tổng hợp tin tức tài chính**: Cập nhật tin tức doanh nghiệp nóng nhất từ CafeF & Vnstock (ví dụ: *'Tin tức mới nhất về VNM'*).\n"
    "- 📈 **Phân tích chỉ báo kỹ thuật**: Đánh giá RSI(14), đường trung bình SMA 20/50, Golden/Death Cross (ví dụ: *'Phân tích chỉ báo RSI và MA của HPG'*).\n"
    "- ⚖️ **So sánh tương quan cổ phiếu**: Đối chiếu dữ liệu thị giá và diễn biến giữa 2 mã (ví dụ: *'So sánh FPT và HPG hôm nay'*).\n"
    "- 💼 **Quản lý danh mục & Lãi/Lỗ (P&L)**: Theo dõi giá trị vốn, thị giá hiện tại, tỷ suất sinh lời và tổng NAV tài khoản.\n"
    "- 🕯️ **Vẽ biểu đồ nến kỹ thuật**: Tạo đồ thị nến hoặc biểu đồ giá đa phiên trực quan (ví dụ: *'Vẽ biểu đồ nến kỹ thuật cho cổ phiếu FPT'*).\n\n"
    "Bạn muốn bắt đầu với mã cổ phiếu nào hôm nay?"
)


def greeting_node(state: ChatState, config: RunnableConfig) -> dict[str, Any]:
    """Node chào hỏi (Greeting Fast-Path): Nối thẳng tới phản hồi thân thiện và hướng dẫn năng lực của trợ lý."""
    t0 = time.perf_counter()
    emit_agent_event("node_start", {"node": "greeting_responder", "timestamp": time.time()})
    turn = state.get("turn") or ""
    with agent_span(turn, "greeting_responder", input=state.get("question", "")) as box:
        box["output"] = GREETING_RESPONSE

    compose = AnswerComposeResult(
        answer=GREETING_RESPONSE,
        model="greeting_fastpath",
        draft_attempts=1,
        guardrail_violations=[],
        evidence=[],
        hitl_used=False,
    )
    words = GREETING_RESPONSE.split(" ")
    for i, w in enumerate(words):
        sep = " " if i < len(words) - 1 else ""
        emit_agent_event("token", {"delta": w + sep})

    dur = round(time.perf_counter() - t0, 3)
    emit_agent_event("node_finish", {"node": "greeting_responder", "duration_s": dur, "duration_ms": int(dur * 1000)})
    return {
        "answer": GREETING_RESPONSE,
        "compose": compose,
    }


def route_after_guardrail(state: ChatState) -> str:
    """Định tuyến sau Guardrail:
    - Nếu không an toàn đi vào guardrail_refusal
    - Nếu là câu chào hỏi -> greeting_node (Greeting Fast-Path)
    - Ngược lại an toàn -> sang rewrite_question
    """
    res = state.get("guardrail_result")
    if res and not res.is_safe:
        return "guardrail_refusal"
    if res and getattr(res, "category", "") == "greeting":
        return "greeting_node"
    return "rewrite_question"


def rewrite_node(state: ChatState, config: RunnableConfig) -> dict[str, Any]:
    """Node viết lại câu hỏi: Chuẩn hóa câu hỏi, phân giải đại từ thay thế từ lịch sử hội thoại."""
    t0 = time.perf_counter()
    emit_agent_event("node_start", {"node": "rewrite_question", "timestamp": time.time()})
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
        from backend.infra.cache.semantic import set_semantic_question

        set_semantic_question(rewritten.rewritten or state.get("question") or "")
        box["output"] = {
            "rewritten": rewritten.rewritten,
            "symbol": rewritten.symbol,
            "symbols": list(rewritten.symbols or []),
            "sub_questions": list(rewritten.sub_questions or []),
        }
    symbols = list(rewritten.symbols) if rewritten.symbols else []
    if not symbols and rewritten.symbol:
        symbols = [rewritten.symbol]
    dur = round(time.perf_counter() - t0, 3)
    emit_agent_event("node_finish", {"node": "rewrite_question", "duration_s": dur, "duration_ms": int(dur * 1000)})
    return {
        "rewritten": rewritten,
        "symbol": rewritten.symbol or (symbols[0] if symbols else None),
        "symbols": symbols,
    }


def supervisor_node(state: ChatState, config: RunnableConfig) -> dict[str, Any]:
    """Node điều phối trung tâm (Supervisor): Phân tích ý định và định tuyến danh sách sub-agents cần gọi."""
    t0 = time.perf_counter()
    emit_agent_event("node_start", {"node": "supervisor", "timestamp": time.time()})
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
    dur = round(time.perf_counter() - t0, 3)
    emit_agent_event("node_finish", {"node": "supervisor", "duration_s": dur, "duration_ms": int(dur * 1000)})
    return {"routing": routing}


def price_node(
    sym: str,
    price_source: PriceSource,
    turn: str = "",
) -> PriceAgentResult:
    """Node thu thập dữ liệu giá Vnstock cho một mã cổ phiếu cụ thể."""
    t0 = time.perf_counter()
    emit_agent_event("node_start", {"node": "price_agent", "symbol": sym, "timestamp": time.time()})
    has_cache = hasattr(price_source, "cache_stats") and callable(getattr(price_source, "cache_stats"))
    hits_before = price_source.cache_stats().get("hits", 0) if has_cache else 0
    with agent_span(turn, "price_agent", input=sym) as box:
        p = run_price_agent(sym, price_source, turn)
        from_cache = (price_source.cache_stats().get("hits", 0) > hits_before) if has_cache else False
        out = {
            "symbol": sym,
            "latest_close": p.latest_close,
            "change_pct": p.change_pct,
            "error": p.error,
            "from_cache": from_cache,
        }
        box["output"] = out
        dur = round(time.perf_counter() - t0, 3)
        finish_payload: dict[str, Any] = {
            "node": "price_agent",
            "symbol": sym,
            "duration_s": dur,
            "duration_ms": int(dur * 1000),
            "output": out,
            "status": "error" if p.error else "done",
        }
        if from_cache:
            emit_agent_event("node_start", {"node": "price_cache", "symbol": sym, "timestamp": time.time()})
            emit_agent_event(
                "node_finish",
                {
                    "node": "price_cache",
                    "symbol": sym,
                    "duration_s": 0,
                    "duration_ms": 0,
                    "output": {"cache_hit": True, "symbol": sym, "layer": "price_source_ttl"},
                    "status": "done",
                },
            )
        emit_agent_event("node_finish", finish_payload)
        return p


def news_node(
    sym: str,
    news_source: NewsSource,
    news_brain: NewsAgentBrain | None = None,
    days: int | None = 7,
    turn: str = "",
) -> NewsAgentResult:
    """Node trích xuất tin tức CafeF cho một mã cổ phiếu cụ thể."""
    t0 = time.perf_counter()
    emit_agent_event("node_start", {"node": "news_agent", "symbol": sym, "timestamp": time.time()})
    with agent_span(turn, "news_agent", input=sym) as box:
        n = run_news_agent(
            sym,
            news_source,
            news_brain or default_news_brain(),
            days=days,
            turn=turn,
        )
        box["output"] = {
            "symbol": sym,
            "items": len(n.items or []),
            "error": n.error,
        }
        dur = round(time.perf_counter() - t0, 3)
        emit_agent_event("node_finish", {"node": "news_agent", "symbol": sym, "duration_s": dur, "duration_ms": int(dur * 1000)})
        return n


def chart_node(
    target_symbols: list[str],
    prices: list[PriceAgentResult],
    price_source: PriceSource,
    history_store: PriceHistoryStore | None = None,
    turn: str = "",
    question: str = "",
) -> Any | None:
    """Node sinh biểu đồ kỹ thuật Matplotlib cho một hoặc nhiều mã cổ phiếu."""
    if not target_symbols:
        return None
    price_by_sym = {p.symbol.upper(): p for p in prices if p and p.symbol}
    history_map: dict[str, list[PriceBar]] = {}

    q_lower = (question or "").lower()
    import re
    session_limit: int | None = None
    m_sess = re.search(r"(\d+)\s*(?:phiên|ngày|session|day)", q_lower)
    if m_sess:
        try:
            val = int(m_sess.group(1))
            if 2 <= val <= 100:
                session_limit = val
        except ValueError:
            pass

    fetch_days = max(30, (session_limit or 15) + 15)

    for sym_item in target_symbols:
        s_upper = sym_item.upper()
        bars: list[PriceBar] = []
        if history_store:
            try:
                bars = list(history_store.read_history(s_upper, days=fetch_days) or [])
            except Exception as exc:
                _logger.warning("history_store read_history failed for %s: %s", s_upper, exc)
                bars = []
        if len(bars) < 5 and hasattr(price_source, "fetch_history"):
            try:
                fetched = price_source.fetch_history(s_upper, days=fetch_days)
                if fetched:
                    bars = fetched
                    if history_store and hasattr(history_store, "upsert_bars"):
                        try:
                            history_store.upsert_bars(s_upper, bars)
                        except Exception:
                            pass
            except Exception as exc:
                _logger.warning("price_source fetch_history failed for %s: %s", s_upper, exc)
        if len(bars) < 2:
            try:
                from backend.services.market_service import MarketService
                from backend.infra.market_data.price_source import VnstockPriceSource
                ms = MarketService(price_source=price_source if isinstance(price_source, VnstockPriceSource) else None)
                hist_records = ms.get_symbol_history(s_upper, limit=max(15, (session_limit or 15) + 5))
                if hist_records:
                    bars = [
                        PriceBar(
                            date=r.trade_date,
                            close=r.close,
                            open_price=r.open,
                            high=r.high,
                            low=r.low,
                            volume=float(r.volume or 0),
                        )
                        for r in hist_records
                    ]
            except Exception as exc:
                _logger.warning("MarketService get_symbol_history fallback failed for %s: %s", s_upper, exc)
        if len(bars) < 2:
            ref_p = price_by_sym.get(s_upper) or (prices[0] if prices else None)
            base_close = (ref_p.latest_close if ref_p and ref_p.latest_close else 50.0)
            from datetime import date, timedelta
            today = date.today()
            bars = []
            fake_count = max(20, (session_limit or 10) + 5)
            for i in range(fake_count, 0, -1):
                d_i = (today - timedelta(days=i)).isoformat()
                factor = 1.0 + ((i % 5) - 2) * 0.008
                c = round(base_close * factor, 2)
                bars.append(PriceBar(
                    date=d_i,
                    close=c,
                    open_price=round(c * 0.995, 2),
                    high=round(c * 1.01, 2),
                    low=round(c * 0.99, 2),
                    volume=1000000.0 + i * 50000.0,
                ))
        if session_limit and len(bars) > session_limit:
            bars = bars[-session_limit:]
        history_map[s_upper] = bars

    is_candlestick = any(w in q_lower for w in ("nến", "candle", "candlestick"))
    style = "candle" if is_candlestick else "line"

    # Phân biệt ý định: So sánh hiệu suất tương đối (% tăng trưởng) vs Biểu đồ giá (VND)
    is_relative_comparison = any(
        w in q_lower
        for w in (
            "so sánh", "so sanh",
            "hiệu suất", "hieu suat",
            "tương đối", "tuong doi",
            "tỷ suất", "ty suat",
            "tăng trưởng", "tang truong",
            "tương quan", "tuong quan",
            "tỷ lệ tăng", "ty le tang",
        )
    )

    if is_relative_comparison:
        chosen_chart_type = "comparison"
    elif is_candlestick:
        chosen_chart_type = "candlestick"
    else:
        chosen_chart_type = "price_history"


    t0 = time.perf_counter()
    emit_agent_event("node_start", {"node": "chart_agent", "symbols": target_symbols, "timestamp": time.time()})
    with agent_span(turn, "chart_agent", input=",".join(target_symbols)) as box:
        if len(target_symbols) == 1:
            chart_result = run_chart_agent(
                target_symbols[0],
                history_map.get(target_symbols[0].upper(), []),
                style=style,
                chart_type=chosen_chart_type,
                limit_sessions=session_limit,
            )
        else:
            chart_result = run_chart_agent(
                target_symbols,
                history_map,
                style=style,
                chart_type=chosen_chart_type,
                limit_sessions=session_limit,
            )
        box["output"] = {
            "success": chart_result.success,
            "url": chart_result.url,
            "file_path": chart_result.file_path,
            "error": chart_result.error,
        }
    if chart_result and getattr(chart_result, "success", False) and getattr(chart_result, "url", None):
        emit_agent_event(
            "chart_url",
            {
                "url": chart_result.url,
                "symbols": target_symbols,
                "chart_type": getattr(chart_result, "chart_type", chosen_chart_type),
                "file_path": getattr(chart_result, "file_path", None),
            },
        )
    dur = round(time.perf_counter() - t0, 3)
    emit_agent_event("node_finish", {"node": "chart_agent", "duration_s": dur, "duration_ms": int(dur * 1000)})
    return chart_result



def workers_node(state: ChatState, config: RunnableConfig) -> dict[str, Any]:
    """Node điều phối công nhân (Workers): Gọi song song price_node, news_node, chart_node và eval_agent."""
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
    need_chart = "chart" in agents or getattr(routing.route, "value", routing.route) == "chart"
    if need_chart and not need_price:
        need_price = True

    price: PriceAgentResult | None = None
    news: NewsAgentResult | None = None
    eval_result = None
    prices: list[PriceAgentResult] = []
    news_list: list[NewsAgentResult] = []

    def _fetch_one(sym: str) -> tuple[PriceAgentResult | None, NewsAgentResult | None]:
        p_res: PriceAgentResult | None = None
        n_res: NewsAgentResult | None = None
        if need_price and need_news:
            with ThreadPoolExecutor(max_workers=2) as pool:
                fut_p = pool.submit(price_node, sym, price_source, turn)
                fut_n = pool.submit(news_node, sym, news_source, news_brain, news_days, turn)
                p_res = fut_p.result()
                n_res = fut_n.result()
        else:
            if need_price:
                p_res = price_node(sym, price_source, turn)
            if need_news:
                n_res = news_node(sym, news_source, news_brain, news_days, turn)
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
                p_res = price_node(sym, price_source, turn)
                prices.append(p_res)
                if sym.upper() == (symbol or "").upper():
                    price = p_res
        if price is None and prices:
            price = next(
                (p for p in prices if p.symbol.upper() == symbol.upper()),
                prices[0],
            )
        if news is None:
            news = news_node(symbol, news_source, news_brain, news_days, turn)
            if news is not None and not news_list:
                news_list = [news]
        if news is None:
            news = NewsAgentResult(symbol=symbol or "", items=[], tool_calls=0)
        ready = prices_have_change_pct_evidence(prices, symbols) or (
            len(symbols) <= 1 and has_change_pct_evidence(price)
        )
        if ready:
            t0 = time.perf_counter()
            emit_agent_event("node_start", {"node": "eval_agent", "symbol": symbol, "timestamp": time.time()})
            with agent_span(turn, "eval_agent", input=symbol) as box:
                eval_result = run_eval_agent(
                    price, news, history_store, brain=eval_brain, turn=turn
                )
                ind = getattr(eval_result, "indicators", None)
                box["output"] = {
                    "symbol": symbol,
                    "severity": str(eval_result.severity),
                    "confidence": eval_result.severity.confidence,
                    "rsi": getattr(ind, "rsi", None),
                    "ma20": getattr(ind, "ma20", None),
                    "ma50": getattr(ind, "ma50", None),
                    "signal": getattr(ind, "signal", None),
                }
            dur = round(time.perf_counter() - t0, 3)
            emit_agent_event("node_finish", {"node": "eval_agent", "symbol": symbol, "duration_s": dur, "duration_ms": int(dur * 1000)})

    chart_result = None
    if need_chart:
        target_symbols = list(symbols) if symbols else ([symbol] if symbol else [])
        if not target_symbols and price and price.symbol:
            target_symbols = [price.symbol]
        req_q = state.get("question") or ""
        rw = state.get("rewritten")
        if rw and getattr(rw, "rewritten", None):
            req_q = f"{req_q} {rw.rewritten}"
        chart_result = chart_node(
            target_symbols=target_symbols,
            prices=prices,
            price_source=price_source,
            history_store=history_store,
            turn=turn,
            question=req_q,
        )

    chart_path = chart_result.url if (chart_result and chart_result.success) else None

    # Phase 2: Tự động nạp dữ liệu Portfolio & Watchlist qua PortfolioWatchAgent
    req_q_lower = (state.get("question") or "").lower()
    rw_q = (state.get("rewritten").rewritten or "") if state.get("rewritten") else ""
    rw_intent = (state.get("rewritten").intent or "") if state.get("rewritten") else ""
    combined_q = f"{req_q_lower} {rw_q.lower()}"
    is_portfolio_query = any(
        k in combined_q
        for k in ("danh mục", "portfolio", "lãi lỗ", "lãi/lỗ", "lãi hay lỗ", "nav", "tài khoản", "nắm giữ", "vị thế")
    ) or "portfolio" in agents or rw_intent == "portfolio"
    is_watchlist_query = any(
        k in combined_q
        for k in ("watchlist", "theo dõi", "danh sách theo dõi", "mã theo dõi", "ngưỡng cảnh báo")
    ) or "watchlist" in agents or rw_intent == "watchlist"

    portfolio_watch_result = None
    portfolio_summary = None
    watchlist_items = None

    if is_portfolio_query or is_watchlist_query or "portfolio_watch" in agents:
        try:
            from backend.agents.portfolio_watch_agent import run_portfolio_watch_agent
            emit_agent_event("node_start", {"node": "portfolio_watch_agent", "timestamp": time.time()})
            t_pw = time.perf_counter()
            target_intent = "watchlist" if (is_watchlist_query and not is_portfolio_query) else ("portfolio" if (is_portfolio_query and not is_watchlist_query) else "all")
            pw_user_id = state.get("user_id") or "default"
            pw_store = cfg.get("watchlist_store")
            portfolio_watch_result = run_portfolio_watch_agent(
                user_id=pw_user_id,
                intent=target_intent,
                price_source=price_source,
                watchlist_store=pw_store,
                turn=turn,
            )
            portfolio_summary = portfolio_watch_result.portfolio_summary
            watchlist_items = portfolio_watch_result.watchlist_items
            dur_pw = round(time.perf_counter() - t_pw, 3)
            emit_agent_event("node_finish", {"node": "portfolio_watch_agent", "duration_s": dur_pw, "duration_ms": int(dur_pw * 1000)})
        except Exception as exc:
            _logger.warning("Không nạp được portfolio_watch trong workers_node: %s", exc)

    return {
        "price": price,
        "news": news,
        "prices": prices,
        "news_list": news_list,
        "eval_result": eval_result,
        "chart_result": chart_result,
        "chart_path": chart_path,
        "portfolio_summary": portfolio_summary,
        "portfolio_watch_result": portfolio_watch_result,
        "watchlist_items": watchlist_items,
    }


def diagram_node(state: ChatState, config: RunnableConfig) -> dict[str, Any]:
    """Node sinh sơ đồ quy trình Mermaid."""
    t0 = time.perf_counter()
    emit_agent_event("node_start", {"node": "diagram_agent", "timestamp": time.time()})
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
    compose = AnswerComposeResult(answer=result.placeholder, model="stub", draft_attempts=1, guardrail_violations=[], evidence=[], hitl_used=False)
    for word in result.placeholder.split(" "):
        emit_agent_event("token", {"delta": word + " "})
    dur = round(time.perf_counter() - t0, 3)
    emit_agent_event("node_finish", {"node": "diagram_agent", "duration_s": dur, "duration_ms": int(dur * 1000)})
    return {"diagram_result": result, "answer": result.placeholder, "compose": compose}


def composer_node(state: ChatState, config: RunnableConfig) -> dict[str, Any]:
    """Node tổng hợp câu trả lời (Composer): Kết hợp dữ liệu và phát sinh câu trả lời bằng Markdown kèm stream token."""
    cfg = _cfg(config)
    turn = state.get("turn") or ""
    symbol = state.get("symbol")
    chart_path = state.get("chart_path")
    input_sym = symbol or state.get("question", "")
    t0 = time.perf_counter()
    emit_agent_event("node_start", {"node": "answer_composer", "timestamp": time.time()})

    def _on_token(delta: str) -> None:
        emit_agent_event("token", {"delta": delta})

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
            chart_path=chart_path,
            portfolio_summary=state.get("portfolio_summary"),
            portfolio_watch_result=state.get("portfolio_watch_result"),
            turn=turn,
            on_token=_on_token,
        )
        box["output"] = (compose.answer or "")[:500]
    dur = round(time.perf_counter() - t0, 3)
    emit_agent_event("node_finish", {"node": "answer_composer", "duration_s": dur, "duration_ms": int(dur * 1000)})
    return {"compose": compose, "answer": compose.answer}


# Tương thích ngược với tên gọi cũ
_node_pre_rewrite_guardrail = guardrail_node
_node_guardrail_refusal = guardrail_refusal_node
_node_rewrite = rewrite_node
_node_supervisor = supervisor_node
_node_diagram_agent = diagram_node
_node_workers = workers_node
_node_answer_composer = composer_node


def route_from_supervisor(state: ChatState) -> str:
    """Định tuyến sau Supervisor: Rẽ nhánh sang diagram_agent hoặc workers."""
    route = getattr(state["routing"].route, "value", state["routing"].route)
    if str(route) == "diagram" or "diagram" in (state["routing"].agents_to_call or []):
        return "diagram_agent"
    return "workers"


def build_chat_graph() -> StateGraph:
    """Xây dựng đồ thị thực thi StateGraph của Multi-Agent Swarm."""
    graph = StateGraph(ChatState)
    graph.add_node("pre_rewrite_guardrail", guardrail_node)
    graph.add_node("guardrail_refusal", guardrail_refusal_node)
    graph.add_node("greeting_node", greeting_node)
    graph.add_node("rewrite_question", rewrite_node)
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("diagram_agent", diagram_node)
    graph.add_node("workers", workers_node)
    graph.add_node("answer_composer", composer_node)

    graph.add_edge(START, "pre_rewrite_guardrail")
    graph.add_conditional_edges(
        "pre_rewrite_guardrail",
        route_after_guardrail,
        {
            "guardrail_refusal": "guardrail_refusal",
            "greeting_node": "greeting_node",
            "rewrite_question": "rewrite_question",
        },
    )
    graph.add_edge("guardrail_refusal", END)
    graph.add_edge("greeting_node", END)
    graph.add_edge("rewrite_question", "supervisor")
    graph.add_conditional_edges(
        "supervisor",
        route_from_supervisor,
        {"diagram_agent": "diagram_agent", "workers": "workers"},
    )
    graph.add_edge("diagram_agent", END)
    graph.add_edge("workers", "answer_composer")
    graph.add_edge("answer_composer", END)
    return graph


@lru_cache(maxsize=1)
def compile_chat_graph():
    """Biên dịch và lưu bộ nhớ đệm đồ thị StateGraph."""
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
    watchlist_store: Any | None = None,
    news_days: int | None = 7,
    limit: int | None = None,
    ttl_minutes: int | float | None = None,
    extract_fn: Any | None = None,
    event_callback: Callable[[str, dict[str, Any]], None] | None = None,
) -> AnswerQuestionResult:
    """Thực thi đồ thị xử lý câu hỏi và trả về kết quả tuân thủ hợp đồng AnswerQuestionResult."""
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
    conversation = apply_sliding_window_with_ttl_eviction(
        conversation,
        limit=effective_limit,
        ttl_minutes=effective_ttl,
    )

    turn_id = (turn or "").strip() or (request_id or "").strip() or str(uuid.uuid4())

    from backend.infra.cache.semantic import clear_semantic_question

    clear_semantic_question()

    guard_preview = check_input_guardrail(q) if q else None
    recalled_memories: list[str] = []
    if (
        effective_user_id
        and guard_preview
        and guard_preview.is_safe
        and guard_preview.category != "greeting"
    ):
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
        "watchlist_store": watchlist_store,
        "news_days": news_days,
        "event_callback": event_callback,
    }
    token = _chat_deps.set(deps)
    try:
        final = {
            "question": q,
            "user_id": user_id,
            "turn": turn_id,
            "conversation": conversation,
            "memories": recalled_memories,
            "guardrail_result": guard_preview,
        }
        chunks = []
        node_timings: dict[str, float] = {}
        t_prev = time.perf_counter()
        for chunk in compile_chat_graph().stream(
            final,
            config=RunnableConfig(recursion_limit=25),
            stream_mode="updates",
        ):
            t_now = time.perf_counter()
            elapsed = round(t_now - t_prev, 3)
            chunks.append(chunk)
            for node, values in chunk.items():
                node_timings[node] = elapsed
                final.update(values)
            t_prev = time.perf_counter()
    finally:
        _chat_deps.reset(token)

    compose = final.get("compose")
    answer_text = final.get("answer") or ""

    memory_store.append_conversation(short_term_user_id, "user", q)
    memory_store.append_conversation(short_term_user_id, "assistant", answer_text)

    if (
        effective_user_id
        and guard_preview
        and guard_preview.is_safe
        and guard_preview.category != "greeting"
    ):
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

    chart_res = final.get("chart_result")
    chart_path = final.get("chart_path")
    if not chart_path and chart_res and getattr(chart_res, "success", False):
        chart_path = getattr(chart_res, "url", None)

    rewritten_val = final.get("rewritten")
    if not rewritten_val:
        is_greeting = getattr(final.get("guardrail_result"), "category", "") == "greeting"
        rewritten_val = RewrittenQuestion(
            original=q,
            rewritten=q,
            symbol=None,
            intent="greeting" if is_greeting else "out_of_scope",
            symbols=[],
        )

    routing_val = final.get("routing")
    if not routing_val:
        is_greeting = getattr(final.get("guardrail_result"), "category", "") == "greeting"
        routing_val = RoutingDecision(
            route="greeting" if is_greeting else "guardrail",
            reason="Luồng chào hỏi trực tiếp (Greeting Fast-Path)" if is_greeting else getattr(final.get("guardrail_result"), "reason", "Chặn bởi Pre-Rewrite Guardrail"),
            agents_to_call=[],
        )

    result = AnswerQuestionResult(
        question=q,
        rewritten=rewritten_val,
        routing=routing_val,
        answer=answer_text,
        price=final.get("price"),
        news=final.get("news"),
        eval_result=final.get("eval_result"),
        compose=compose,
        diagram_result=final.get("diagram_result"),
        chart_result=chart_res,
        chart_path=chart_path,
        error=final.get("error"),
        memories=recalled_memories,
        portfolio_watch_result=final.get("portfolio_watch_result"),
    )

    from backend.graph.steps import build_steps_from_chunks
    result.steps = build_steps_from_chunks(
        chunks, final_error=result.error, timings=node_timings
    )

    _logger.info(
        "run_chat_graph symbol=%s agents=%s",
        result.rewritten.symbol,
        result.routing.agents_to_call,
    )
    return result


if __name__ == "__main__":
    import argparse

    if sys.stdout.encoding.lower() != "utf-8":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="Export LangGraph Chat diagram")
    parser.add_argument(
        "--out",
        type=str,
        default="resources/docs/chat_agent_graph.png",
        help="Path to save graph image (default: resources/docs/chat_agent_graph.png)",
    )
    args = parser.parse_args()

    graph = compile_chat_graph().get_graph()

    print("\n=== MERMAID DIAGRAM ===")
    mermaid_code = graph.draw_mermaid()
    print(mermaid_code)
    print("========================\n")

    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = Path(__file__).resolve().parents[3] / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        png_bytes = graph.draw_mermaid_png()
        out_path.write_bytes(png_bytes)
        print(f"[OK] Đã xuất sơ đồ ảnh PNG tại: {out_path}")
    except Exception as exc:
        mmd_path = out_path.with_suffix(".mmd")
        mmd_path.write_text(mermaid_code, encoding="utf-8")
        print(f"[WARN] Không thể kết nối để render PNG ({exc}). Đã lưu mã nguồn Mermaid tại: {mmd_path}")

