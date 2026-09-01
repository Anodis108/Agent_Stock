"""Nodes hub — coordinator là máy trạng thái, không phải crawler.

Giống agent_m2 `agent_node`: LLM `bind_tools` + retrieval (`need_*`). Khác chỗ
tool *không chạy việc*: `need_price` chỉ trả mã; `route_coordinator` `Send`
subgraph PriceAgent (ReAct + vnstock). Lý do: HITL ghi DB phải đứng ở hub
(`interrupt_before=["hitl_commit"]`) — nếu PriceAgent tự HITL thì 5 chỗ dừng.

`rewrite_question` (đầu graph): cùng ý `retriever._rewrite_query` — viết lại
câu user trước recall + lập plan; `question` gốc giữ cho history/eval.

`coordinator` chạy lại mỗi sóng (DB → crawl → eval → synth → HITL → reply).
`plan_turn == turn` thì không gọi LLM plan lần nữa — chỉ đọc `next_wave`.
`Send` đợt gather (price+news) hội tụ `after_wave1` rồi về hub; eval/synth
một nhánh, về thẳng coordinator.

`_hydrate_from_db`: cache hit → biến hàng sqlite thành price/news, khỏi crawl.
"""

from __future__ import annotations

from datetime import date

from langgraph.types import Send

from app.agent_pr import context, memory
from app.agent_pr.craw_agent.schemas import Agent_Output as PriceOut
from app.agent_pr.db_agent.nodes import approve_pending_write
from app.agent_pr.db_agent.schemas import Agent_Output as DbOut
from app.agent_pr.db_agent.schemas import PendingWrite
from app.agent_pr.news_agent.schemas import Agent_Output as NewsOut
from app.agent_pr.news_agent.schemas import NewsItem
from app.agent_pr.supervisor_agent.schemas import Agent_Output, AgentPlan, MemoryFact, RewrittenQuery
from app.agent_pr.supervisor_agent.state import SupervisorState
from app.config import settings
from app.llm.completion import chat_parsed
from app.llm.params import DETERMINISTIC
from app.agent_pr._llm import invoke_with_tools
from app.agent_pr.react import use_offline_tools
from app.guardrails.injection import bound_messages
from app.agent_pr.supervisor_agent.tools import TOOLS as SUPERVISOR_TOOLS
from app.agent_pr.tool_selection import select_tools
from app.monitoring.tracing import step_parent, trace_step

# Giống LEGAL_SYSTEM_PROMPT (persona + quy tắc) và _SUPERVISOR_SYSTEM agent_m2
# (worker không nói với nhau; chỉ chọn việc, không tự làm).
_PLAN_SYSTEM = """Bạn là Hierarchical Coordinator hỏi–đáp cổ phiếu niêm yết Việt Nam.

Nhiệm vụ: CHỈ đánh dấu loại dữ liệu cần qua tool need_* — không crawl, không chấm, không ghép câu.
Worker (Price/News/DB/Eval/Synth) không nói với nhau; bạn giao việc, họ báo cáo hub.

Quy tắc:
- Gọi MỌI need_* mà câu hỏi thật sự cần (có thể nhiều tool cùng lúc). Bạn chỉ thấy một phần catalog.
- need_price = giá đóng cửa / % phiên trước. need_news = tin CafeF thô.
- need_db = nêu lịch sử đã lưu. need_eval = chấm tin vs giá — CHỈ khi cũng need_price VÀ need_news.
- need_synth = ghép câu cho user (gần như luôn).
- Argument symbol: mã HOSE/HNX/UPCOM (thường 3 chữ: HPG, VNM, FPT). Tách từ câu hoặc hội thoại. Không bịa mã.
- Không bịa số liệu. Không gọi tool ngoài need_*.

Ví dụ:
- "giá HPG bao nhiêu" → need_price + need_synth
- "tin FPT" → need_news + need_synth
- "tại sao HPG giảm" → need_price + need_news + need_eval + need_synth
- "lưu/ghi tin chưa có" → need_news + need_db + need_synth
- follow-up "còn LPB thì sao?" → lấy mã LPB từ câu, cùng loại dữ liệu lượt trước nếu rõ"""

# Cùng ý retriever._rewrite_query + ngày hiện tại (agent_m2 _system_prompt).
_REWRITE_SYSTEM = """Bạn là chuyên gia tìm kiếm thông tin cổ phiếu niêm yết Việt Nam.

Viết lại câu hỏi thành MỘT query rõ ràng để điều phối agent (giá vnstock, tin CafeF, lịch sử DB).
Giữ / tách mã CP nếu nhận ra (HPG, FPT, …). Làm rõ đại từ ("nó", "mã đó") từ hội thoại gần đây.
Không trả lời câu hỏi. Không bịa mã. Chỉ trả về câu đã viết lại, không giải thích."""


def _query_for_plan(state: SupervisorState) -> str:
    return str(state.get("rewritten_question") or state.get("question") or "").strip()


def rewrite_question(state: SupervisorState) -> dict:
    """Viết lại câu hỏi — cùng kiểu retriever._rewrite_query. Giữ `question` gốc."""
    original = str(state.get("question") or "").strip()
    with trace_step(step_parent(state), "rewrite_question", input=original) as t:
        rewritten = original
        extra_symbol = ""
        if original and not use_offline_tools():
            history = list(state.get("history") or [])
            user = f"Hôm nay: {date.today().isoformat()}\nCâu hỏi: {original}"
            if history:
                shaped = context.sliding_window(history, settings.agent_keep_recent_messages)
                user = (
                    f"Hôm nay: {date.today().isoformat()}\n"
                    f"Hội thoại gần đây:\n{context.format_messages(shaped)}\n\n"
                    f"Câu hỏi hiện tại: {original}"
                )
            try:
                parsed = chat_parsed(
                    bound_messages(_REWRITE_SYSTEM, user),
                    RewrittenQuery,
                    DETERMINISTIC,
                )
                rewritten = (parsed.query or "").strip() or original
                extra_symbol = parsed.symbol
            except Exception:
                rewritten = original
                extra_symbol = ""
        t["output"] = rewritten or "skip"
        out: dict = {"rewritten_question": rewritten}
        if extra_symbol and not str(state.get("symbol") or "").strip():
            out["symbol"] = extra_symbol
        if rewritten and rewritten != original:
            out["trace"] = list(state.get("trace") or []) + [f"Rewrite: {rewritten}"]
        return out


def _sanitize_plan(raw: AgentPlan, hint: str) -> AgentPlan:
    """Hint user thắng LLM; eval cần giá+tin; luôn bật synth."""
    symbol = (hint or raw.symbol or "").strip().upper()
    use_price, use_news, use_db = raw.use_price, raw.use_news, raw.use_db
    use_eval = bool(raw.use_eval and use_price and use_news)
    use_synth = True
    if not any((use_price, use_news, use_db, use_eval)):
        use_price = True
    return AgentPlan(
        symbol=symbol,
        use_price=use_price,
        use_news=use_news,
        use_db=use_db,
        use_eval=use_eval,
        use_synth=use_synth,
        reasoning=raw.reasoning,
    )


def _call_name_args(call) -> tuple[str, dict]:
    if isinstance(call, dict):
        return str(call.get("name") or ""), dict(call.get("args") or {})
    name = str(getattr(call, "name", None) or "")
    args = getattr(call, "args", None) or {}
    return name, dict(args)


def _plan_from_tool_calls(calls: list, hint: str, question: str) -> AgentPlan:
    parsed = [_call_name_args(c) for c in calls]
    names = {name for name, _ in parsed if name}
    symbol = hint
    for _name, args in parsed:
        if args.get("symbol"):
            symbol = str(args["symbol"])
            break
    raw = AgentPlan(
        symbol=symbol or "HPG",
        use_price="need_price" in names,
        use_news="need_news" in names,
        use_db="need_db" in names,
        use_eval="need_eval" in names,
        use_synth="need_synth" in names or True,
        reasoning=",".join(sorted(n for n in names if n)),
    )
    return _sanitize_plan(raw, hint or symbol)


def _make_plan(
    question: str,
    hint: str,
    history: list | None = None,
    memories: list | None = None,
) -> AgentPlan:
    """LLM bind top-k tool need_* (retrieval) — không chat_parsed."""
    parts = [
        f"Hôm nay: {date.today().isoformat()}",
        f"Câu hỏi: {question}\nMã gợi ý (có thể trống): {hint or '(không có)'}",
    ]
    if memories:
        parts.append("Đã biết về user:\n" + "\n".join(f"- {m}" for m in memories))
    if history:
        shaped = context.sliding_window(history, settings.agent_max_messages)
        parts.append("Hội thoại gần đây:\n" + context.format_messages(shaped))
    user = "\n\n".join(parts)
    query = question or hint
    relevant = select_tools(query, SUPERVISOR_TOOLS)
    if use_offline_tools():
        calls = [
            {"name": "need_price", "args": {"symbol": hint or "HPG"}},
            {"name": "need_news", "args": {"symbol": hint or "HPG"}},
            {"name": "need_eval", "args": {"symbol": hint or "HPG"}},
            {"name": "need_synth", "args": {"symbol": hint or "HPG"}},
        ]
        return _plan_from_tool_calls(calls, hint, question)
    try:
        response = invoke_with_tools(
            bound_messages(_PLAN_SYSTEM, user),
            relevant or SUPERVISOR_TOOLS,
        )
    except Exception:
        calls = [
            {"name": "need_price", "args": {"symbol": hint or "HPG"}},
            {"name": "need_synth", "args": {"symbol": hint or "HPG"}},
        ]
        return _plan_from_tool_calls(calls, hint, question)
    calls = getattr(response, "tool_calls", None) or []
    if not calls:
        calls = [
            {"name": "need_price", "args": {"symbol": hint or "HPG"}},
            {"name": "need_synth", "args": {"symbol": hint or "HPG"}},
        ]
    return _plan_from_tool_calls(calls, hint, question)


def _same_symbol(obj: object | None, symbol: str) -> bool:
    return bool(obj and getattr(obj, "symbol", None) == symbol)


def _from_db(obj: object | None) -> bool:
    src = str(getattr(obj, "source", "") or "")
    return src == "db" or src.startswith("db")


def _has_price(state: SupervisorState, symbol: str) -> bool:
    """Đủ giá để khỏi crawl: có last VÀ % so với phiên trước (1 hàng DB thì chưa)."""
    price = state.get("price")
    return bool(
        _same_symbol(price, symbol)
        and getattr(price, "last", 0)
        and getattr(price, "pct_change", None) is not None
    )


def _has_news(state: SupervisorState, symbol: str) -> bool:
    news = state.get("news")
    return bool(_same_symbol(news, symbol) and (getattr(news, "articles", None) or []))


def _news_candidates(news: object | None) -> list[dict]:
    """NewsItem → dict title/url cho stage_writes. Bỏ tin lấy từ DB."""
    if news is None or _from_db(news):
        return []
    articles = getattr(news, "articles", None) or []
    out: list[dict] = []
    for item in articles:
        url = str(getattr(item, "url", "") or "").strip()
        title = str(getattr(item, "title", "") or "").strip()
        if url:
            out.append({"title": title, "url": url})
    return out


def _price_candidates(price: object | None) -> list[dict]:
    """PriceOut → 1 phiên mới nhất để soạn ghi. Bỏ giá lấy từ DB / crawl lỗi."""
    if price is None or _from_db(price):
        return []
    last = float(getattr(price, "last", 0) or 0)
    date = str(getattr(price, "trading_date", "") or "").strip()
    if last <= 0 or not date:
        return []
    return [{"trading_date": date, "close": last}]


def _price_from_db(db: object | None) -> PriceOut | None:
    rows = getattr(db, "price_history", None) or []
    if not rows:
        return None
    last = float(rows[0].close)
    prev = float(rows[1].close) if len(rows) >= 2 else None
    pct = round((last - prev) / prev * 100, 2) if prev else None
    return PriceOut(
        symbol=str(getattr(db, "symbol", "")),
        last=last,
        prev_close=prev,
        pct_change=pct,
        trading_date=str(rows[0].trading_date),
        source="db",
    )


def _news_from_db(db: object | None) -> NewsOut | None:
    saved = getattr(db, "saved_news", None) or []
    if not saved:
        return None
    return NewsOut(
        symbol=str(getattr(db, "symbol", "")),
        articles=[NewsItem(title=n.title, url=n.url) for n in saved],
        source="db",
    )


def _hydrate_from_db(state: SupervisorState, plan: AgentPlan) -> dict:
    """Cache hit: biến hàng DB thành price/news để khỏi crawl."""
    db = state.get("db")
    if db is None or getattr(db, "symbol", None) != plan.symbol:
        return {}
    extra: dict = {}
    if plan.use_price and not _has_price(state, plan.symbol):
        price = _price_from_db(db)
        if price:
            extra["price"] = price
    if plan.use_news and not _has_news(state, plan.symbol):
        news = _news_from_db(db)
        if news:
            extra["news"] = news
    return extra


def _lookup_done(state: SupervisorState, turn: str, symbol: str) -> bool:
    if turn:
        return state.get("db_lookup_turn") == turn
    return _same_symbol(state.get("db"), symbol)


def _write_done(state: SupervisorState, turn: str) -> bool:
    return bool(turn) and state.get("db_write_turn") == turn


def _needs_lookup(plan: AgentPlan) -> bool:
    return bool(plan.use_price or plan.use_news or plan.use_db)


def _pending_gather(state: SupervisorState, plan: AgentPlan) -> list[str]:
    """Crawl còn thiếu SAU khi đã đọc DB (và hydrate nếu có)."""
    symbol = plan.symbol
    pending: list[str] = []
    if plan.use_price and not _has_price(state, symbol):
        pending.append("price_agent")
    if plan.use_news and not _same_symbol(state.get("news"), symbol):
        pending.append("news_agent")
    return pending


def _should_stage(state: SupervisorState, plan: AgentPlan) -> bool:
    """Còn dữ liệu vừa crawl (không lấy từ DB) thì soạn lệnh ghi."""
    return bool(_news_candidates(state.get("news")) or _price_candidates(state.get("price")))


def _pending_list(db: object | None) -> list[PendingWrite]:
    return list(getattr(db, "pending_writes", None) or [])


def coordinator(state: SupervisorState) -> dict:
    """Hub. Lần đầu: LLM lập plan. Mọi lần: DB → crawl nếu thiếu → eval → synth → HITL.

    Span con trực tiếp dưới root (step_parent(state) không kèm agent_name —
    coordinator chạy ở cấp hub, không phải bên trong 1 subgraph con).
    """
    with trace_step(
        step_parent(state),
        "coordinator",
        input=str(state.get("question") or state.get("symbol") or ""),
    ) as t:
        out = _coordinate(state)
        t["output"] = out.get("next_wave")
        return out


def _coordinate(state: SupervisorState) -> dict:
    hint = str(state.get("symbol") or "").strip().upper()
    question = str(state.get("question") or hint or "").strip()
    if not question:
        from app.agent_pr.synthesis_agent.schemas import Agent_Output as SynthOut

        msg = "Lỗi: cần mã cổ phiếu hoặc câu hỏi. Hãy nêu rõ (vd. HPG hôm nay sao)."
        return {
            "next_wave": "done",
            "trace": list(state.get("trace") or []) + [msg],
            "draft": SynthOut(answer=msg),
        }
    plan_query = _query_for_plan(state) or question

    turn = str(state.get("turn") or "")
    fresh_plan = state.get("plan_turn") != turn
    trace = list(state.get("trace") or [])
    extra: dict = {}

    if fresh_plan:
        plan = _make_plan(
            plan_query,
            hint,
            history=list(state.get("history") or []),
            memories=list(state.get("memories") or []),
        )
        trace.append(f"Coordinator LLM: {plan.symbol} · {plan.reasoning}")
        extra = {
            "symbol": plan.symbol,
            "question": question,
            "plan": plan,
            "plan_turn": turn,
        }
        state = {**state, **extra}
    else:
        plan = state["plan"]

    hydrated = _hydrate_from_db(state, plan)
    if hydrated:
        extra = {**extra, **hydrated}
        state = {**state, **hydrated}
        if not fresh_plan:
            used = [k for k in ("price", "news") if k in hydrated]
            if used:
                trace.append("DB đã có " + " + ".join(used) + " — dùng luôn")

    if _needs_lookup(plan) and not _lookup_done(state, turn, plan.symbol):
        if not fresh_plan:
            trace.append("Đọc DB trước")
        return {**extra, "next_wave": "db_lookup", "trace": trace}

    pending = _pending_gather(state, plan)
    if pending:
        if not fresh_plan:
            trace.append(f"DB chưa đủ → crawl {', '.join(pending)}")
        return {**extra, "next_wave": "gather", "trace": trace}

    if (
        plan.use_eval
        and state.get("eval_turn") != turn
        and _same_symbol(state.get("price"), plan.symbol)
        and _same_symbol(state.get("news"), plan.symbol)
    ):
        if not fresh_plan:
            trace.append("Giao EvalAgent")
        return {**extra, "next_wave": "eval", "trace": trace}

    if plan.use_synth and state.get("synth_turn") != turn:
        n = len(state["db"].price_history) if state.get("db") else 0
        if not fresh_plan:
            trace.append("Giao SynthesisAgent")
        return {**extra, "next_wave": "synth", "n_history": n, "trace": trace}

    skip_hitl = bool(state.get("skip_hitl"))
    if _should_stage(state, plan) and not _write_done(state, turn):
        if not fresh_plan:
            trace.append("Soạn lệnh ghi dữ liệu vừa crawl")
        return {**extra, "next_wave": "db_write", "trace": trace}

    if _pending_list(state.get("db")) and not skip_hitl:
        if not fresh_plan:
            trace.append("HITL — chờ duyệt trước khi ghi DB")
        return {**extra, "next_wave": "hitl", "trace": trace}

    if not fresh_plan:
        trace.append("Đủ theo plan → trả user")
    return {**extra, "next_wave": "done", "trace": trace}


def _send(state: SupervisorState, node: str, payload: dict) -> Send:
    """Nhánh Send chỉ thấy payload — luôn kèm `turn` (string, pickle-safe) để
    node đích tự tìm span cha qua step_parent/agent_span. KHÔNG kèm span object
    thật — MemorySaver checkpoint có thể serialize payload này, span không pickle được.
    """
    return Send(node, payload)


def route_coordinator(state: SupervisorState) -> str | list[Send]:
    """Map `next_wave` → node hoặc Send. Gather: một worker / vòng (dễ debug)."""
    wave = state["next_wave"]
    symbol = str(state.get("symbol") or "")
    turn = str(state.get("turn") or "")
    if wave == "db_lookup":
        return [
            _send(
                state,
                "db_agent",
                {
                    "symbol": symbol,
                    "turn": turn,
                    "mode": "read",
                    "candidate_news": [],
                    "candidate_prices": [],
                },
            )
        ]
    if wave == "gather":
        names = _pending_gather(state, state["plan"])
        return [_send(state, names[0], {"symbol": symbol, "turn": turn})] if names else "reply"
    if wave == "db_write":
        return [
            _send(
                state,
                "db_agent",
                {
                    "symbol": symbol,
                    "turn": turn,
                    "mode": "write",
                    "candidate_news": _news_candidates(state.get("news")),
                    "candidate_prices": _price_candidates(state.get("price")),
                },
            )
        ]
    if wave == "eval":
        return "eval_agent"
    if wave == "synth":
        return "synth_agent"
    if wave == "hitl":
        return "hitl_commit"
    return "reply"


def hitl_commit(state: SupervisorState) -> dict:
    """Chạy sau interrupt_before — user đã đồng ý (hoặc còn lệnh pending chưa quyết).

    Duyệt lệnh status=pending. Lệnh user đã từ chối qua /pr/approve giữ rejected
    (approve_pending_write không đảo).
    """
    with trace_step(step_parent(state), "hitl_commit", input=str(state.get("symbol") or "")) as t:
        out = _hitl_commit(state)
        t["output"] = out.get("trace", [""])[-1] if out.get("trace") else ""
        return out


def _hitl_commit(state: SupervisorState) -> dict:
    db = state.get("db")
    pending = _pending_list(db)
    symbol = str(state.get("symbol") or (getattr(db, "symbol", "") if db else ""))
    n_ok = 0
    for pw in pending:
        try:
            if approve_pending_write(pw.id, approve=True, kind=pw.kind or "news"):
                n_ok += 1
        except Exception:
            continue
    from app.agent_pr.db_agent.nodes import _read_rows
    from app.agent_pr.db_agent.schemas import PriceRow, SavedNews

    rows = _read_rows(symbol) if symbol else {"price_rows": [], "news_rows": []}
    refreshed = DbOut(
        symbol=symbol,
        price_history=[PriceRow(**row) for row in rows["price_rows"]],
        saved_news=[SavedNews(**row) for row in rows["news_rows"]],
        pending_writes=[],
        detail=f"HITL: đã COMMIT {n_ok} lệnh vào DB",
    )
    line = refreshed.detail
    return {
        "db": refreshed,
        "trace": list(state.get("trace") or []) + [line],
    }


def after_wave1(state: SupervisorState) -> dict:
    """Fan-in gather — chỉ tóm worker đã về (không bắt buộc đủ 3)."""
    bits: list[str] = []
    if state.get("price"):
        bits.append(f"giá {state['price'].source}")
    if state.get("news"):
        bits.append(f"{len(state['news'].articles)} tin {state['news'].source}")
    if state.get("db"):
        n_pending = len(state["db"].pending_writes or [])
        db_bit = f"DB {len(state['db'].price_history)} phiên + {len(state['db'].saved_news)} tin"
        if n_pending:
            db_bit += f" · {n_pending} lệnh chờ HITL"
        bits.append(db_bit)
    line = "gather về hub: " + (" + ".join(bits) if bits else "(trống)")
    return {"trace": list(state.get("trace") or []) + [line]}


def reply(state: SupervisorState) -> dict:
    """Đóng gói. Có draft thì dùng; không thì 1 câu tối thiểu từ báo cáo đã có."""
    with trace_step(step_parent(state), "reply", input=str(state.get("question") or "")) as t:
        out = _reply(state)
        output = out.get("output")
        t["output"] = getattr(output, "answer", None)
        return out


def _reply(state: SupervisorState) -> dict:
    plan = state.get("plan")
    symbol = str(state.get("symbol") or (plan.symbol if plan else ""))
    draft = state.get("draft")
    if draft:
        answer = draft.answer
        db = state.get("db")
        if db and str(db.detail or "").startswith("HITL:"):
            answer = answer.rstrip() + " " + db.detail
    else:
        parts = [f"{symbol}:"]
        if state.get("price") and state["price"].pct_change is not None:
            p = state["price"]
            chieu = "giảm" if p.pct_change < 0 else "tăng"
            parts.append(f"giá {chieu} {abs(p.pct_change):.1f}%.")
        elif state.get("news"):
            parts.append(f"{len(state['news'].articles)} tin CafeF.")
        else:
            parts.append("đã thu thập xong theo plan.")
        db = state.get("db")
        n_pending = len(db.pending_writes) if db else 0
        if n_pending:
            parts.append(
                f"Đã soạn {n_pending} lệnh ghi bài chưa có trong kho "
                "(chờ duyệt HITL — chưa COMMIT vào bảng news)."
            )
        elif db and db.detail:
            parts.append(db.detail)
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
    return {
        "output": output,
        "history": [{"role": "assistant", "content": output.answer}],
    }


def compact_history(state: SupervisorState) -> dict:
    """Chỉ chạy khi should_compact_route chọn node này (>40% window)."""
    history = list(state.get("history") or [])
    compacted = context.summarize_old_messages(
        history, settings.agent_keep_recent_messages
    )
    return {"history": context.set_history(compacted)}


def should_compact_route(state: SupervisorState) -> str:
    """Nguyên tắc 40–60%: vượt 40% window → compact; không thì thẳng coordinator."""
    history = list(state.get("history") or [])
    if context.should_compact(history, settings.agent_context_window_tokens):
        return "compact_history"
    return "coordinator"


def recall_memory(state: SupervisorState) -> dict:
    """Đầu lượt: đọc long-term (Qdrant user_memory) theo user_id. Không user → bỏ qua."""
    with trace_step(step_parent(state), "recall_memory", input=str(state.get("user_id") or "")) as t:
        out = _recall_memory(state)
        t["output"] = {"n_memories": len(out.get("memories") or [])}
        return out


def _recall_memory(state: SupervisorState) -> dict:
    user_id = str(state.get("user_id") or "").strip()
    original = str(state.get("question") or "")
    query = _query_for_plan(state) or original
    memories: list[str] = []
    if user_id:
        try:
            memories = memory.recall_long_term(user_id, query)
        except Exception:
            memories = []
    updates: dict = {"memories": memories}
    if original:
        updates["history"] = [{"role": "user", "content": original}]
    return updates


def store_memory(state: SupervisorState) -> dict:
    """Cuối lượt: trích 1 sự thật dài hạn về user (mã theo dõi, khẩu vị) → vector store."""
    with trace_step(step_parent(state), "store_memory", input=str(state.get("user_id") or "")) as t:
        out = _store_memory(state)
        t["output"] = bool(out)
        return out


def _store_memory(state: SupervisorState) -> dict:
    user_id = str(state.get("user_id") or "").strip()
    if not user_id:
        return {}
    recent = context.sliding_window(
        list(state.get("history") or []), settings.agent_keep_recent_messages
    )
    if not recent:
        return {}
    lines = context.format_messages(recent)
    try:
        parsed = chat_parsed(
            bound_messages(
                "Trích sự thật DÀI HẠN về user từ hội thoại cổ phiếu. "
                "Chỉ mã theo dõi, khẩu vị rủi ro, quyết định đã chốt — không tóm giá/tin phiên.",
                lines,
            ),
            MemoryFact,
            DETERMINISTIC,
        )
    except Exception:
        return {}
    fact = (parsed.fact or "").strip()
    if parsed.worth_saving and fact and fact.upper() != "NONE":
        memory.save_to_long_term(user_id, fact)
    return {}
