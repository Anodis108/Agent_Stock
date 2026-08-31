"""Nodes hub — LLM chọn worker, không crawl / không chấm / không ghi DB.

Giống hierarchical.py: Supervisor quyết định ai chạy. Khác: 1 lần chat_parsed
lập AgentPlan (cờ từng agent), rồi thực thi plan — worker độc lập, báo cáo hub.

Eval chỉ khi đã có giá+tin. Gather (price/news/db được chọn và chưa có đúng mã)
Send song song. Trong 1 lượt không gọi LLM plan lại. Lượt HTTP mới: `turn` uuid
→ lập plan mới; short-term `history` (compact nếu đầy) + long-term `memories`
đưa vào prompt. Context: `app.agent_pr.context` — compact_history persist,
`_make_plan` chỉ sliding + reinject tạm.
"""

from __future__ import annotations

from langgraph.types import Send

from app.agent_pr import context, memory
from app.agent_pr.symbol import normalize_symbol
from app.agent_pr.supervisor_agent.schemas import Agent_Output, AgentPlan
from app.agent_pr.supervisor_agent.state import SupervisorState
from app.config import settings
from app.llm.completion import chat_parsed
from app.llm.params import DETERMINISTIC
from app.monitoring.tracing import trace_step

_PLAN_SYSTEM = """Bạn là Hierarchical Coordinator hỏi–đáp cổ phiếu niêm yết Việt Nam.

Chọn worker nào CẦN cho câu hỏi. Worker không nói với nhau — chỉ báo cáo bạn.
Tách mã CP từ câu (HOSE/HNX/UPCOM, thường 3 chữ: HPG, VNM, MWG, …).

- price: giá đóng cửa, % so phiên trước
- news: tin CafeF
- db: lịch sử đã lưu trong DB
- eval: chấm tin tốt/xấu vs chiều giá — CHỈ true nếu cũng bật price VÀ news
- synth: ghép câu trả lời có cấu trúc cho user (thường true)

Ví dụ: "giá HPG bao nhiêu" → chỉ price (+ synth). "tin FPT" → news (+ synth).
"tại sao HPG giảm" / câu phân tích chung → bật đủ price, news, eval, synth; db nếu cần lịch sử.
Nếu có lịch sử hội thoại / thông tin đã biết về user: dùng để chọn mã và worker, không bịa số liệu."""

# Nhắc lại ở CUỐI prompt lập plan (reinject) — system dài + history dễ bị
# lost-in-the-middle; 3 dòng này là phần không được quên khi chọn worker.
_PLAN_REMINDER = (
    "Chỉ chọn worker cần thiết. Eval chỉ khi có cả price và news. "
    "Tách đúng mã niêm yết VN. Không bịa giá / tin."
)


def _sanitize_plan(raw: AgentPlan, hint: str) -> AgentPlan:
    """Chốt mã hợp lệ; Eval bắt buộc có giá+tin; không để plan rỗng."""
    if hint:
        symbol = normalize_symbol(hint)
    else:
        symbol = normalize_symbol(raw.symbol)
    use_price, use_news, use_db = raw.use_price, raw.use_news, raw.use_db
    use_eval = bool(raw.use_eval and use_price and use_news)
    use_synth = raw.use_synth
    if not any((use_price, use_news, use_db, use_eval, use_synth)):
        use_price, use_synth = True, True
    return AgentPlan(
        symbol=symbol,
        use_price=use_price,
        use_news=use_news,
        use_db=use_db,
        use_eval=use_eval,
        use_synth=use_synth,
        reasoning=raw.reasoning,
    )


def _make_plan(
    question: str,
    hint: str,
    history: list | None = None,
    memories: list | None = None,
) -> AgentPlan:
    """Một lời gọi OpenAI structured output — não của hub.

    History đưa vào prompt là bản SHAPE TẠM (sliding_window + format), không
    ghi đè state — compaction persist nằm ở compact_history. Reinject chỉ
    dẫn ở cuối list message (không phải trong chuỗi user) để chống fade-out.
    """
    parts = [f"Câu hỏi: {question}\nMã gợi ý (có thể trống): {hint or '(không có)'}"]
    if memories:
        parts.append("Đã biết về user:\n" + "\n".join(f"- {m}" for m in memories))
    if history:
        shaped = context.sliding_window(history, settings.agent_max_messages)
        parts.append("Hội thoại gần đây:\n" + context.format_messages(shaped))
    raw = chat_parsed(
        context.reinject_instructions(
            [
                {"role": "system", "content": _PLAN_SYSTEM},
                {"role": "user", "content": "\n\n".join(parts)},
            ],
            _PLAN_REMINDER,
        ),
        AgentPlan,
        DETERMINISTIC,
    )
    return _sanitize_plan(raw, hint)


def _same_symbol(obj: object | None, symbol: str) -> bool:
    return bool(obj and getattr(obj, "symbol", None) == symbol)


def _pending_gather(state: SupervisorState, plan: AgentPlan) -> list[str]:
    """Worker đợt thu thập chưa có báo cáo ĐÚNG MÃ (checkpoint lượt trước khác mã thì fetch lại)."""
    symbol = plan.symbol
    pending: list[str] = []
    price = state.get("price")
    if plan.use_price and not (_same_symbol(price, symbol) and getattr(price, "last", 0)):
        pending.append("price_agent")
    news = state.get("news")
    if plan.use_news and not _same_symbol(news, symbol):
        pending.append("news_agent")
    db = state.get("db")
    if plan.use_db and not _same_symbol(db, symbol):
        pending.append("db_agent")
    return pending


def coordinator(state: SupervisorState) -> dict:
    """Hub. Lần đầu: LLM lập plan. Các lần sau: chọn đợt tiếp theo plan."""
    hint = str(state.get("symbol") or "").strip().upper()
    question = str(state.get("question") or hint or "").strip()
    span = state.get("_trace_span")

    with trace_step(span, "coordinator", input=question or hint) as t:
        if not question:
            raise ValueError("Cần symbol hoặc question")

        trace = list(state.get("trace") or [])
        turn = str(state.get("turn") or "")
        need_plan = state.get("plan_turn") != turn

        # Mã gửi sẵn sai định dạng → fail trước khi tốn API (lượt mới).
        if hint:
            try:
                hint = normalize_symbol(hint)
            except ValueError:
                if need_plan:
                    raise
                hint = ""
        if need_plan:
            plan = _make_plan(
                question,
                hint,
                history=list(state.get("history") or []),
                memories=list(state.get("memories") or []),
            )
            trace.append(f"Coordinator LLM: {plan.symbol} · {plan.reasoning}")
            pending = _pending_gather({**state, "plan": plan, "symbol": plan.symbol}, plan)
            if pending:
                wave = "gather"
            elif plan.use_eval:
                wave = "eval"
            elif plan.use_synth:
                wave = "synth"
            else:
                wave = "done"
            out = {
                "symbol": plan.symbol,
                "question": question,
                "plan": plan,
                "plan_turn": turn,
                "next_wave": wave,
                "trace": trace,
            }
            t["output"] = {"next_wave": wave, "plan": plan.model_dump()}
            return out

        plan = state["plan"]
        pending = _pending_gather(state, plan)
        if pending:
            trace.append(f"Giao gather → {', '.join(pending)}")
            out = {"next_wave": "gather", "trace": trace}
            t["output"] = {"next_wave": "gather", "pending": pending}
            return out

        if (
            plan.use_eval
            and state.get("eval_turn") != turn
            and _same_symbol(state.get("price"), plan.symbol)
            and _same_symbol(state.get("news"), plan.symbol)
        ):
            trace.append("Giao EvalAgent")
            out = {"next_wave": "eval", "trace": trace}
            t["output"] = {"next_wave": "eval"}
            return out

        if plan.use_synth and state.get("synth_turn") != turn:
            n = len(state["db"].price_history) if state.get("db") else 0
            trace.append("Giao SynthesisAgent")
            out = {"next_wave": "synth", "n_history": n, "trace": trace}
            t["output"] = {"next_wave": "synth"}
            return out

        trace.append("Đủ theo plan → trả user")
        out = {"next_wave": "done", "trace": trace}
        t["output"] = {"next_wave": "done"}
        return out


def route_coordinator(state: SupervisorState) -> str | list[Send]:
    """Gather: Send đúng worker còn thiếu. Eval/synth/reply: 1 cạnh."""
    wave = state["next_wave"]
    if wave == "gather":
        plan = state["plan"]
        symbol = state["symbol"]
        sends = [
            Send(name, {"symbol": symbol})
            for name in _pending_gather(state, plan)
        ]
        return sends or "reply"
    if wave == "eval":
        return "eval_agent"
    if wave == "synth":
        return "synth_agent"
    return "reply"


def after_wave1(state: SupervisorState) -> dict:
    """Fan-in gather — chỉ tóm worker đã về (không bắt buộc đủ 3)."""
    bits: list[str] = []
    if state.get("price"):
        bits.append(f"giá {state['price'].source}")
    if state.get("news"):
        bits.append(f"{len(state['news'].articles)} tin {state['news'].source}")
    if state.get("db"):
        bits.append(f"DB {len(state['db'].price_history)} phiên")
    line = "gather về hub: " + (" + ".join(bits) if bits else "(trống)")
    with trace_step(state.get("_trace_span"), "after_wave1", input=state.get("symbol", "")) as t:
        t["output"] = line
        return {"trace": list(state.get("trace") or []) + [line]}


def reply(state: SupervisorState) -> dict:
    """Đóng gói. Có draft thì dùng; không thì 1 câu tối thiểu từ báo cáo đã có."""
    plan = state.get("plan")
    symbol = str(state.get("symbol") or (plan.symbol if plan else ""))
    draft = state.get("draft")
    if draft:
        answer = draft.answer
    else:
        parts = [f"{symbol}:"]
        if state.get("price") and state["price"].pct_change is not None:
            p = state["price"]
            chieu = "giảm" if p.pct_change < 0 else "tăng"
            parts.append(f"giá {chieu} {abs(p.pct_change):.1f}%.")
        elif state.get("news"):
            parts.append(f"{len(state['news'].articles)} tin.")
        else:
            parts.append("đã thu thập xong theo plan.")
        answer = " ".join(parts)

    output = Agent_Output(
        symbol=symbol,
        question=str(state.get("question") or ""),
        answer=answer,
        price=state.get("price"),
        news=state.get("news"),
        eval=state.get("eval"),
        db=state.get("db"),
        trace=list(state.get("trace") or []),
        plan=plan,
    )
    with trace_step(state.get("_trace_span"), "reply", input=symbol) as t:
        t["output"] = output.answer
        return {
            "output": output,
            "history": [{"role": "assistant", "content": output.answer}],
        }


def mark_eval(state: SupervisorState) -> dict:
    """Gắn eval với turn hiện tại — không phụ thuộc subgraph copy field `turn`."""
    return {"eval_turn": str(state.get("turn") or "")}


def mark_synth(state: SupervisorState) -> dict:
    """Gắn draft với turn hiện tại — re-synth mỗi lượt hỏi."""
    return {"synth_turn": str(state.get("turn") or "")}


def compact_history(state: SupervisorState) -> dict:
    """Sau recall: history vượt 40% window → tóm tắt phần cũ, GHI ĐÈ state.

    Giống compact_node agent_m2: persist bản nén để lượt sau không gọi LLM
    tóm tắt lại. Dưới ngưỡng → {}. Reducer chỉ thay list khi nhận set_history.
    """
    history = list(state.get("history") or [])
    span = state.get("_trace_span")
    with trace_step(span, "compact_history", input={"n": len(history)}) as t:
        if not context.should_compact(history, settings.agent_context_window_tokens):
            t["output"] = "skip"
            return {}
        compacted = context.summarize_old_messages(
            history, settings.agent_keep_recent_messages
        )
        t["output"] = {"n_before": len(history), "n_after": len(compacted)}
        return {"history": context.set_history(compacted)}


def recall_memory(state: SupervisorState) -> dict:
    """Đầu lượt: đọc long-term (Qdrant user_memory) theo user_id. Không user → bỏ qua."""
    user_id = str(state.get("user_id") or "").strip()
    question = str(state.get("question") or "")
    span = state.get("_trace_span")
    with trace_step(span, "recall_memory", input=user_id or "(none)") as t:
        memories: list[str] = []
        if user_id:
            try:
                memories = memory.recall_long_term(user_id, question)
                t["output"] = {"n": len(memories)}
            except Exception as exc:
                t["output"] = {"n": 0, "error": str(exc)}
        else:
            t["output"] = {"n": 0}
        updates: dict = {"memories": memories}
        if question:
            updates["history"] = [{"role": "user", "content": question}]
        return updates


def store_memory(state: SupervisorState) -> dict:
    """Cuối lượt: trích 1 sự thật dài hạn về user (mã theo dõi, khẩu vị) → vector store."""
    user_id = str(state.get("user_id") or "").strip()
    span = state.get("_trace_span")
    with trace_step(span, "store_memory", input=user_id or "(none)") as t:
        if not user_id:
            t["output"] = "skip"
            return {}
        recent = context.sliding_window(
            list(state.get("history") or []), settings.agent_keep_recent_messages
        )
        if not recent:
            t["output"] = "empty"
            return {}
        lines = context.format_messages(recent)
        from app.llm import completion
        from app.llm.params import GenerationParams

        try:
            fact = completion.chat(
                [
                    {
                        "role": "user",
                        "content": (
                            "Trích 1 sự thật DÀI HẠN về user từ hội thoại cổ phiếu "
                            "(mã đang theo dõi, sở thích, khẩu vị rủi ro). "
                            'Một câu, hoặc "NONE".\n\n'
                            + lines
                        ),
                    }
                ],
                GenerationParams(temperature=0.0),
            ).strip()
        except Exception as exc:
            t["output"] = f"error: {exc}"
            return {}
        if fact and fact.upper() != "NONE":
            memory.save_to_long_term(user_id, fact)
            t["output"] = fact
        else:
            t["output"] = "NONE"
        return {}
