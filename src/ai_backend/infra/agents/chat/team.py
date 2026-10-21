"""Team chat của Hierarchical Swarm — các node riêng của nhánh hỏi-đáp + entrypoint `run_chat_graph`.

Graph dựng ở graph.py:
top_supervisor ➔ guardrail_input ➔ (vi phạm / chào hỏi) ───────────────────────────────┐
                                 ➔ rewrite_question ➔ chat_supervisor ⇄ scan_supervisor ⇄ price/news │
                                                                     ⇄ eval / draw / portfolio       │
                                                                     ➔ concept_retrieval ──────────┤
                                                                     ➔ ────────────────────────────┴➔ answer ⇄ guardrail_output ➔ END
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Callable

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END

from ai_backend.infra.agents.state import AnswerQuestionResult
from ai_backend.infra.agents.steps import build_chat_steps
from ai_backend.infra.agents.chat.answer_composer import (
    MAX_DRAFT_ATTEMPTS,
    AnswerComposeResult,
    AnswerDraftBrain,
    check_answer,
    draft_answer,
    safe_fallback_answer,
)
from ai_backend.infra.agents.chat.answer_composer.nodes import sanitize_answer_chart_markdown
from ai_backend.domain.guardrails.output_checks import find_buy_sell_phrases, has_evidence_grounding, strip_buy_sell
from ai_backend.infra.agents.scan.eval_agent import EvalAgentBrain
from ai_backend.infra.agents.scan.news_agent import NewsAgentBrain
from ai_backend.infra.agents.chat.supervisor_agent import (
    RewriteBrain,
    RewrittenQuestion,
    SupervisorBrain,
    recall_memory,
    rewrite_question,
    store_memory,
)
from common.domain.entities import RoutingDecision
from ai_backend.domain.guardrails import check_input_guardrail
from common.domain.ports import (
    MemoryStore,
    NewsSource,
    PriceHistoryStore,
    PriceSource,
)
from ai_backend.infra.agents.events import (  # noqa: F401 — re-export cho web_backend / llm
    StreamCancelledError,
    check_stream_cancelled,
    emit_agent_event,
    graph_deps,
    set_stream_cancel_event,
)
from ai_backend.infra.agents.state import SwarmState
from ai_backend.infra.monitoring.tracing import agent_span, mark_turn_guardrail
from ai_backend.infra.storage.memory_store import (
    apply_sliding_window_with_ttl_eviction,
    filter_conversation_history,
)
from common.logging import get_logger
from common.settings import settings

_logger = get_logger(__name__)
def _cfg(_config: RunnableConfig) -> dict[str, Any]:
    return graph_deps.get()


# ==============================================================================
# Agent Nodes
# ==============================================================================

def guardrail_input_node(state: SwarmState, config: RunnableConfig) -> dict[str, Any]:
    """Guardrail đầu vào: chặn Prompt Injection, câu hỏi ngoài phạm vi; nhận diện câu chào thuần."""
    t0 = time.perf_counter()
    emit_agent_event("node_start", {"node": "guardrail_input", "timestamp": time.time()})
    turn = state.get("turn") or ""
    q = state.get("question", "")
    res = state.get("guardrail_result") or check_input_guardrail(q)
    with agent_span(turn, "guardrail_input", input=q) as box:
        box["output"] = {
            "is_safe": res.is_safe,
            "category": res.category,
            "reason": res.reason,
        }
    if not res.is_safe:
        mark_turn_guardrail(turn)
    dur = round(time.perf_counter() - t0, 3)
    emit_agent_event("node_finish", {"node": "guardrail_input", "duration_s": dur, "duration_ms": int(dur * 1000)})
    return {
        "question": q,
        "guardrail_result": res,
    }


def route_after_guardrail(state: SwarmState) -> str:
    """Vi phạm hoặc câu chào thuần → trả lời thẳng (answer); còn lại → rewrite_question."""
    res = state.get("guardrail_result")
    if res and (not res.is_safe or getattr(res, "category", "") == "greeting"):
        return "answer"
    return "rewrite_question"


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


def rewrite_node(state: SwarmState, config: RunnableConfig) -> dict[str, Any]:
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
        from ai_backend.infra.cache.semantic import set_semantic_question

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


def concept_retrieval_node(state: SwarmState, config: RunnableConfig) -> dict[str, Any]:
    """Lấy đoạn giải thích khái niệm từ Qdrant (kèm source_file); answer sẽ trả lời bằng đoạn này."""
    t0 = time.perf_counter()
    emit_agent_event("node_start", {"node": "concept_retrieval", "timestamp": time.time()})
    cfg = _cfg(config)
    question = state.get("question") or ""
    from ai_backend.infra.qdrant.answer import NOT_IN_DOCS, answer_concept

    client = cfg.get("concept_client")
    if client is None:
        from ai_backend.infra.storage.long_term_memory import get_qdrant_client

        client = get_qdrant_client()
    if client is None:
        found_answer, source_file = NOT_IN_DOCS, None
    else:
        found = answer_concept(question, client=client)
        found_answer, source_file = found.answer, found.source_file
    dur = round(time.perf_counter() - t0, 3)
    emit_agent_event(
        "node_finish",
        {
            "node": "concept_retrieval",
            "duration_s": dur,
            "duration_ms": int(dur * 1000),
            "source_file": source_file,
        },
    )
    return {"concept_answer": found_answer, "source_file": source_file}


def answer_node(state: SwarmState, config: RunnableConfig) -> dict[str, Any]:
    """Soạn câu trả lời gửi khách hàng (chưa qua guardrail_output).

    Trả lời thẳng: từ chối (guardrail_input chặn), câu chào, khái niệm (concept_retrieval), sơ đồ (draw_agent).
    Còn lại: LLM soạn từ dữ liệu worker; lượt soạn lại nhận vi phạm từ guardrail_output.
    """
    cfg = _cfg(config)
    turn = state.get("turn") or ""
    t0 = time.perf_counter()
    emit_agent_event("node_start", {"node": "answer", "timestamp": time.time()})

    def _on_token(delta: str) -> None:
        emit_agent_event("token", {"delta": delta})

    res = state.get("guardrail_result")
    attempt = int(state.get("answer_attempts") or 0)
    evidence: list[str] = []
    model = "direct"
    if res is not None and not res.is_safe:
        kind = "refusal"
        text = res.refusal_response or "Yêu cầu không thuộc phạm vi xử lý của hệ thống."
    elif res is not None and getattr(res, "category", "") == "greeting":
        kind, text = "greeting", GREETING_RESPONSE
    elif state.get("concept_answer") is not None:
        kind, text = "concept", state["concept_answer"]
    elif state.get("diagram_result") is not None and state.get("chart_result") is None:
        kind, text = "diagram", state["diagram_result"].placeholder
    else:
        kind = "composed"
        text = ""

    with agent_span(turn, "answer", input={"kind": kind, "attempt": attempt}) as box:
        if kind == "composed":
            rewritten = state.get("rewritten")
            text, evidence, model, is_direct = draft_answer(
                question=(rewritten.rewritten if rewritten else "") or state.get("question") or "",
                symbol=state.get("symbol"),
                price=state.get("price"),
                news=state.get("news"),
                eval_result=state.get("eval_result"),
                user_id=state.get("user_id") or "default",
                brain=cfg.get("answer_brain"),
                prices=state.get("prices") or None,
                news_list=state.get("news_list") or None,
                chart_path=state.get("chart_path"),
                portfolio_summary=state.get("portfolio_summary"),
                portfolio_watch_result=state.get("portfolio_watch_result"),
                turn=turn,
                on_token=_on_token,
                attempt=attempt,
                previous_violations=state.get("guardrail_violations") or [],
            )
            if is_direct:
                kind = "portfolio"
        else:
            words = text.split(" ")
            for i, w in enumerate(words):
                _on_token(w + (" " if i < len(words) - 1 else ""))
        box["output"] = (text or "")[:500]

    dur = round(time.perf_counter() - t0, 3)
    emit_agent_event("node_finish", {"node": "answer", "duration_s": dur, "duration_ms": int(dur * 1000)})
    update: dict[str, Any] = {
        "answer": text,
        "answer_kind": kind,
        "answer_model": model,
        "answer_evidence": evidence,
        "answer_attempts": attempt + 1,
    }
    if kind == "composed" and has_evidence_grounding(text, evidence):
        update["last_grounded"] = text
    return update


def guardrail_output_node(state: SwarmState, config: RunnableConfig) -> dict[str, Any]:
    """Guardrail đầu ra trước khi gửi khách hàng.

    - Câu trả lời LLM soạn: cấm khuyên mua/bán chắc chắn, số liệu phải khớp evidence. Vi phạm → quay lại
      answer soạn lại (tối đa MAX_DRAFT_ATTEMPTS lượt); hết lượt → viết lại an toàn từ evidence.
    - Trả lời thẳng (từ chối, chào, khái niệm, sơ đồ, bảng danh mục): gỡ cụm khuyên mua/bán nếu có.
    """
    t0 = time.perf_counter()
    emit_agent_event("node_start", {"node": "guardrail_output", "timestamp": time.time()})
    turn = state.get("turn") or ""
    kind = state.get("answer_kind") or "composed"
    answer = state.get("answer") or ""
    evidence = list(state.get("answer_evidence") or [])
    attempts = int(state.get("answer_attempts") or 1)
    res = state.get("guardrail_result")

    with agent_span(turn, "guardrail_output", input={"kind": kind, "attempt": attempts}) as box:
        violations: list[str] = []
        retry = False
        if kind == "composed":
            violations = check_answer(answer, evidence, attempts - 1)
            if not violations:
                final = sanitize_answer_chart_markdown(answer)
            elif attempts < MAX_DRAFT_ATTEMPTS:
                retry = True
            else:
                final, violations = safe_fallback_answer(state.get("last_grounded") or "", answer, evidence)
        else:
            phrases = find_buy_sell_phrases(answer)
            final = strip_buy_sell(answer) if phrases else answer
            if kind == "refusal" and res is not None:
                violations = [res.reason]
        box["output"] = {"ok": not violations, "retry": retry, "violations": violations}

    dur = round(time.perf_counter() - t0, 3)
    emit_agent_event("node_finish", {"node": "guardrail_output", "duration_s": dur, "duration_ms": int(dur * 1000)})
    if retry:
        return {"guardrail_violations": violations, "next": ["answer"]}
    compose = AnswerComposeResult(
        answer=final,
        model=state.get("answer_model") or "direct",
        draft_attempts=attempts,
        guardrail_violations=violations,
        evidence=evidence,
        hitl_used=False,
    )
    return {"answer": final, "compose": compose, "guardrail_violations": violations, "next": [END]}


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
    account_holdings: list | None = None,
    concept_client: Any | None = None,
    news_days: int | None = 7,
    limit: int | None = None,
    ttl_minutes: int | float | None = None,
    extract_fn: Any | None = None,
    event_callback: Callable[[str, dict[str, Any]], None] | None = None,
) -> AnswerQuestionResult:
    """Thực thi đồ thị xử lý câu hỏi và trả về kết quả tuân thủ hợp đồng AnswerQuestionResult.

    Luồng tổng quát:
      1) Chuẩn bị ngữ cảnh (conversation, turn, clear cache)
      2) Guardrail sớm + recall bộ nhớ dài hạn
      3) Câu rỗng → trả lỗi sớm (không chạy graph)
      4) Gói deps + state → run_swarm_graph (mode=chat)
      5) Lưu hội thoại / memory sau khi có câu trả lời
      6) Map state → AnswerQuestionResult + steps timeline
    """
    # --- 1) Chuẩn bị ngữ cảnh ---
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
    conversation: list[dict[str, Any]] = []
    if memory_store is not None and hasattr(memory_store, "list_conversation"):
        try:
            conversation = memory_store.list_conversation(
                effective_user_id, limit=effective_limit, ttl_minutes=effective_ttl
            )
        except TypeError:
            conversation = memory_store.list_conversation(
                effective_user_id, limit=effective_limit
            )
    conversation = apply_sliding_window_with_ttl_eviction(
        conversation,
        limit=effective_limit,
        ttl_minutes=effective_ttl,
    )

    turn_id = (turn or "").strip() or (request_id or "").strip() or str(uuid.uuid4())

    from ai_backend.infra.cache.semantic import clear_semantic_question

    clear_semantic_question()

    # --- 2) Guardrail sớm + recall memory (bỏ qua greeting) ---
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

    # --- 3) Early return nếu câu hỏi rỗng ---
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

    # --- 4) Chạy swarm graph (guardrail → rewrite → supervisor ⇄ workers → composer) ---
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
        "account_holdings": account_holdings,
        "concept_client": concept_client,
        "news_days": news_days,
        "event_callback": event_callback,
    }
    from ai_backend.infra.agents.graph import run_swarm_graph

    final, chunks, node_timings = run_swarm_graph(
        {
            "mode": "chat",
            "question": q,
            "user_id": user_id,
            "turn": turn_id,
            "conversation": conversation,
            "memories": recalled_memories,
            "guardrail_result": guard_preview,
            "completed": [],
        },
        deps,
    )

    compose = final.get("compose")
    answer_text = final.get("answer") or ""

    # --- 5) Ghi short-term conversation + long-term memory ---
    if memory_store is not None and hasattr(memory_store, "append_conversation"):
        memory_store.append_conversation(effective_user_id, "user", q)
        memory_store.append_conversation(effective_user_id, "assistant", answer_text)

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

    # --- 6) Map state graph → AnswerQuestionResult + timeline steps ---
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
        source_file=final.get("source_file"),
    )

    from ai_backend.infra.agents.steps import build_steps_from_chunks
    result.steps = build_steps_from_chunks(
        chunks, final_error=result.error, timings=node_timings
    )

    _logger.info(
        "run_chat_graph symbol=%s agents=%s",
        result.rewritten.symbol,
        result.routing.agents_to_call,
    )
    return result

