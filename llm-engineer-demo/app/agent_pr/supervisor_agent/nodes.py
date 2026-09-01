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

`_coordinate` là máy trạng thái, mỗi lần hub ghé qua trả đúng MỘT `next_wave`
theo thứ tự ưu tiên cố định (kiểm tra theo đúng thứ tự này, dừng ở điều kiện
đầu tiên khớp):

    coordinator (mỗi lần ghé)
      ├─ thiếu câu hỏi/mã            → done (lỗi)
      ├─ (fresh_plan) chưa lập plan  → gọi LLM plan (need_* tools) 1 lần/turn
      ├─ plan cần price/news/db
      │  và chưa đọc DB turn này     → db_lookup   (Send db_agent mode=read)
      ├─ còn agent CHƯA THỬ crawl    → gather      (Send 1 worker/vòng)
      ├─ có agent ĐÃ THỬ và LỖI      → done (lỗi — chặn retry vô hạn)
      ├─ plan.use_eval và đủ giá+tin → eval        (route "eval_agent")
      ├─ plan.use_synth chưa chạy    → synth       (route "synth_agent")
      ├─ có dữ liệu mới cần ghi      → db_write    (Send db_agent mode=write)
      ├─ có pending chờ duyệt        → hitl        (route "hitl_commit")
      └─ hết việc theo plan          → done        (route "reply")

`_apply_loop_guard` là lưới an toàn ĐỘC LẬP nằm ngoài thứ tự trên: nếu
`next_wave` lặp lại y hệt ≥ `_MAX_SAME_WAVE_STREAK` lần liên tiếp (ví dụ eval/
synth/db_write cứ quay lại vì một lỗi mà `_gather_stuck` chưa lường trước),
buộc dừng với lỗi thay vì chạy tới `recursion_limit` rồi crash khó hiểu.
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
from app.llm.completion import chat_parsed_with_usage
from app.llm.params import DETERMINISTIC
from app.agent_pr._llm import invoke_with_tools
from app.optimization.routing import rule_based_router
from app.guardrails.injection import bound_messages
from app.agent_pr.supervisor_agent.tools import TOOLS as SUPERVISOR_TOOLS
from app.agent_pr.tool_selection import select_tools
from app.monitoring.tracing import pop_usage, record_usage, step_parent, trace_step

# Giống LEGAL_SYSTEM_PROMPT (persona + quy tắc) và _SUPERVISOR_SYSTEM agent_m2
# (worker không nói với nhau; chỉ chọn việc, không tự làm).
_PLAN_SYSTEM = """Bạn là Hierarchical Coordinator hỏi–đáp cổ phiếu niêm yết Việt Nam.

Nhiệm vụ: CHỈ đánh dấu loại dữ liệu cần qua tool need_* — không crawl, không chấm, không ghép câu.
Worker (Price/News/DB/Eval/Synth) không nói với nhau; bạn giao việc, họ báo cáo hub.

Quy tắc:
- Gọi MỌI need_* mà câu hỏi thật sự cần (có thể nhiều tool cùng lúc). Bạn chỉ thấy một phần catalog.
- need_price = giá đóng cửa / % phiên trước. need_news = tin CafeF thô.
- need_db = nêu lịch sử đã lưu. need_synth = ghép câu cho user (gần như luôn).
- need_eval = chấm sentiment tin + đối chiếu khớp giá (EvalAgent BẮT BUỘC cần cả giá và tin,
  thiếu 1 trong 2 sẽ báo lỗi) — nên khi gọi need_eval PHẢI gọi kèm CẢ need_price VÀ need_news.
  Gọi need_eval khi câu hỏi thuộc 1 trong 3 dạng sau (không chỉ đúng chữ "tại sao"):
    1. Hỏi NGUYÊN NHÂN biến động giá — "tại sao/vì sao/do đâu ... tăng/giảm".
    2. Hỏi ĐỘ TIN CẬY / KHỚP của tin — "tin đó có đáng tin không", "tin có khớp giá không",
       "tin xấu/tốt có đúng không", "có phải vì tin ... không".
    3. Hỏi CHẤM/PHÂN LOẠI sentiment — "chấm tin tốt/xấu", "tin nào tiêu cực/tích cực",
       "so tin xấu và tốt", "tốt/xấu/trung lập".
  Chỉ BỎ QUA need_eval khi user rõ ràng nói không cần đánh giá ("đừng đánh giá", "chỉ liệt kê", "không cần chấm").
- Argument symbol: mã HOSE/HNX/UPCOM (thường 3 chữ: HPG, VNM, FPT). Tách từ câu hoặc hội thoại. Không bịa mã.
- Không bịa số liệu. Không gọi tool ngoài need_*.

Ví dụ:
- "giá HPG bao nhiêu" → need_price + need_synth (không cần eval — không hỏi nguyên nhân/độ tin cậy)
- "tin FPT" → need_news + need_synth
- "tại sao HPG giảm" → need_price + need_news + need_eval + need_synth
- "HPG giảm, tin đó có đáng tin không" → need_price + need_news + need_eval + need_synth
- "giá HPG giảm vậy tin có khớp không" → need_price + need_news + need_eval + need_synth
- "chấm từng tin VNM: tốt hay xấu" → need_price + need_news + need_eval + need_synth (eval cần cả 2)
- "chỉ liệt kê headline FPT, đừng đánh giá" → need_news + need_synth (user từ chối eval rõ ràng)
- "lưu/ghi tin chưa có" → need_news + need_db + need_synth
- follow-up "còn LPB thì sao?" → lấy mã LPB từ câu, cùng loại dữ liệu lượt trước nếu rõ"""

# Cùng ý retriever._rewrite_query + ngày hiện tại (agent_m2 _system_prompt).
_REWRITE_SYSTEM = """Bạn là chuyên gia tìm kiếm thông tin cổ phiếu niêm yết Việt Nam.

Viết lại câu hỏi thành MỘT query rõ ràng để điều phối agent (giá vnstock, tin CafeF, lịch sử DB).
Giữ / tách mã CP nếu nhận ra (HPG, FPT, …). Làm rõ đại từ ("nó", "mã đó") từ hội thoại gần đây.
Không trả lời câu hỏi. Không bịa mã. Chỉ trả về câu đã viết lại, không giải thích."""


def _query_for_plan(state: SupervisorState) -> str:
    """Câu dùng để lập plan/recall — ưu tiên bản đã rewrite, fallback câu gốc."""
    return str(state.get("rewritten_question") or state.get("question") or "").strip()


def rewrite_question(state: SupervisorState) -> dict:
    """Viết lại câu hỏi — cùng kiểu retriever._rewrite_query. Giữ `question` gốc."""
    original = str(state.get("question") or "").strip()
    with trace_step(step_parent(state), "rewrite_question", input=original) as t:
        rewritten = original
        extra_symbol = ""
        if original:
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
                parsed, usage = chat_parsed_with_usage(
                    bound_messages(_REWRITE_SYSTEM, user),
                    RewrittenQuery,
                    DETERMINISTIC,
                )
                record_usage(str(state.get("turn") or ""), settings.llm_model, **usage)
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
    """Đọc (name, args) dù `call` là dict thô (offline) hay tool_call object của LangChain."""
    if isinstance(call, dict):
        return str(call.get("name") or ""), dict(call.get("args") or {})
    name = str(getattr(call, "name", None) or "")
    args = getattr(call, "args", None) or {}
    return name, dict(args)


def _plan_from_tool_calls(calls: list, hint: str, question: str) -> AgentPlan:
    """tool_calls (need_price/need_news/...) → AgentPlan thô, rồi `_sanitize_plan` chuẩn hoá."""
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
        use_synth=True,  # luôn ghép câu — _sanitize_plan cũng force lại giá trị này
        reasoning=",".join(sorted(n for n in names if n)),
    )
    return _sanitize_plan(raw, hint or symbol)


# rule_based_router gốc (Bài 8) đo theo độ dài câu — sai với domain này vì câu
# ngắn kiểu "tại sao HPG giảm" vẫn cần price+news+eval (3 worker). Chặn thêm
# keyword đa-nguyên-nhân trước khi rơi về rule_based_router (độ dài) làm fallback.
_HARD_PLAN_KEYWORDS = ("tại sao", "vì sao", "so sánh", "phân tích", "dự đoán", "nên mua")


def _plan_model(query: str) -> str:
    """Câu chứa keyword đa-nguyên-nhân → ép gpt-4o; còn lại theo rule_based_router (độ dài)."""
    if any(kw in query.lower() for kw in _HARD_PLAN_KEYWORDS):
        return "gpt-4o"
    return rule_based_router(query)


def _make_plan(
    question: str,
    hint: str,
    history: list | None = None,
    memories: list | None = None,
    turn: str = "",
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
    try:
        response = invoke_with_tools(
            bound_messages(_PLAN_SYSTEM, user),
            relevant or SUPERVISOR_TOOLS,
            model=_plan_model(query),
            turn=turn,
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
    """`obj` (price/news/db output) có tồn tại và đúng mã đang xử lý không."""
    return bool(obj and getattr(obj, "symbol", None) == symbol)


def _from_db(obj: object | None) -> bool:
    """`obj.source` bắt đầu bằng "db" — dữ liệu hydrate từ DB, không phải vừa crawl."""
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
    """Đủ tin để khỏi crawl: đúng mã và có ít nhất 1 bài."""
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
    """DbOut.price_history (mới nhất trước) → PriceOut giả lập, source="db". None nếu rỗng."""
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
    """DbOut.saved_news → NewsOut giả lập, source="db". None nếu rỗng."""
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
    """Đã đọc DB trong turn hiện tại chưa — fallback so mã nếu thiếu `turn` (test offline)."""
    if turn:
        return state.get("db_lookup_turn") == turn
    return _same_symbol(state.get("db"), symbol)


def _write_done(state: SupervisorState, turn: str) -> bool:
    """Đã COMMIT/soạn ghi DB trong turn hiện tại chưa (db_agent mode=write đã chạy)."""
    return bool(turn) and state.get("db_write_turn") == turn


def _needs_lookup(plan: AgentPlan) -> bool:
    """Plan có cần bất kỳ dữ liệu nào từ DB không (giá, tin, hoặc lịch sử)."""
    return bool(plan.use_price or plan.use_news or plan.use_db)


def _price_failed(price: object | None, symbol: str) -> bool:
    """True nếu đã crawl giá mã này rồi nhưng thất bại (mã sai / vnstock lỗi).

    Price thành công LUÔN có last > 0 (craw_agent/nodes.py:parse) — nên
    last<=0 sau khi đã crawl (cùng symbol) nghĩa là thử rồi và không có kết
    quả, không phải "chưa thử". Phân biệt việc này với _has_price()==False
    (có thể chỉ đang thiếu, chưa crawl) để không retry vô hạn — Repetition
    Detection, Lesson10 Phần 3 (Termination & Error Recovery).
    """
    return _same_symbol(price, symbol) and not getattr(price, "last", 0)


def _news_failed(news: object | None, symbol: str) -> bool:
    """True nếu đã crawl tin mã này rồi nhưng lỗi mạng/API (không phải chỉ rỗng bài).

    Khác price: news rỗng bài (articles=[]) là kết quả HỢP LỆ (mã đúng,
    không có tin) — không nên chặn retry. Chỉ coi là "thất bại" khi có lỗi
    tường minh (source bắt đầu "Lỗi ...") — CafeF lỗi mạng/HTTP thật sự.
    """
    if not _same_symbol(news, symbol):
        return False
    return str(getattr(news, "source", "") or "").startswith("Lỗi")


def _pending_gather(state: SupervisorState, plan: AgentPlan) -> list[str]:
    """Crawl còn thiếu SAU khi đã đọc DB (và hydrate nếu có).

    Bỏ agent đã crawl-và-lỗi khỏi danh sách — retry vô hạn khi mã không hợp
    lệ / crawl lỗi liên tục là nguyên nhân crash recursion_limit trước đây.
    """
    symbol = plan.symbol
    pending: list[str] = []
    if plan.use_price and not _has_price(state, symbol) and not _price_failed(state.get("price"), symbol):
        pending.append("price_agent")
    if (
        plan.use_news
        and not _same_symbol(state.get("news"), symbol)
        and not _news_failed(state.get("news"), symbol)
    ):
        pending.append("news_agent")
    return pending


def _gather_stuck(state: SupervisorState, plan: AgentPlan) -> list[str]:
    """Agent plan bật nhưng đã crawl-và-lỗi, không còn gì để thử lại.

    Khác _pending_gather (chưa thử / còn đáng thử): đây là "đã thử hết,
    vẫn thiếu" — coordinator phải dừng gather, không lặp vô hạn."""
    symbol = plan.symbol
    stuck: list[str] = []
    if plan.use_price and not _has_price(state, symbol) and _price_failed(state.get("price"), symbol):
        stuck.append("price_agent")
    if plan.use_news and not _same_symbol(state.get("news"), symbol) and _news_failed(state.get("news"), symbol):
        stuck.append("news_agent")
    return stuck


def _should_stage(state: SupervisorState, plan: AgentPlan) -> bool:
    """Còn dữ liệu vừa crawl (không lấy từ DB) thì soạn lệnh ghi."""
    return bool(_news_candidates(state.get("news")) or _price_candidates(state.get("price")))


def _pending_list(db: object | None) -> list[PendingWrite]:
    """Danh sách lệnh ghi đang treo (chưa COMMIT) trên DbOut, rỗng nếu chưa có `db`."""
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
        out = _apply_loop_guard(state, out)
        t["output"] = out.get("next_wave")
        return out


def _apply_loop_guard(state: SupervisorState, out: dict) -> dict:
    """Cùng next_wave lặp quá _MAX_SAME_WAVE_STREAK lần liên tiếp → dừng, trả lỗi.

    Không sửa từng nhánh của _coordinate (nhiều return rải rác) — đo streak
    trên kết quả nó vừa trả, độc lập với _gather_stuck (chỉ bắt lặp ở gather).
    """
    wave = out.get("next_wave")
    if wave in (None, "done"):
        out["wave_streak"] = 0
        return out
    streak = (int(state.get("wave_streak") or 0) + 1) if state.get("next_wave") == wave else 1
    if streak < _MAX_SAME_WAVE_STREAK:
        out["wave_streak"] = streak
        return out

    from app.agent_pr.synthesis_agent.schemas import Agent_Output as SynthOut

    msg = f"Coordinator kẹt lặp ở bước '{wave}' {streak} lần liên tiếp — dừng để tránh vòng lặp vô hạn."
    return {
        "next_wave": "done",
        "wave_streak": 0,
        "trace": list(out.get("trace") or state.get("trace") or []) + [msg],
        "draft": SynthOut(answer=msg, confidence=0.0),
    }


# Loop Detection (Lesson 10 Phần 3) — _gather_stuck chỉ bắt lặp ở bước gather
# (crawl giá/tin). Ngưỡng này bắt lặp ở BẤT KỲ next_wave nào (eval/synth/
# db_write quay lại đúng 1 wave nhiều lần vì lỗi khác _gather_stuck chưa lường
# trước) — chặn sớm thay vì chạy tới recursion_limit=28 rồi crash khó hiểu.
_MAX_SAME_WAVE_STREAK = 4


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
            turn=turn,
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

    stuck = _gather_stuck(state, plan)
    if stuck and state.get("stuck_turn") != turn:
        # Đã crawl và lỗi (mã không hợp lệ / nguồn crawl lỗi) — không còn gì để
        # thử lại. Dừng gather ngay tại đây thay vì để plan tiếp tục vòng lặp
        # db_lookup → gather → db_lookup mãi tới recursion_limit (crash 503).
        from app.agent_pr.synthesis_agent.schemas import Agent_Output as SynthOut

        field_by_agent = {"price_agent": "price", "news_agent": "news"}
        detail = "; ".join(
            str(getattr(state.get(field_by_agent[s]), "source", "") or "") for s in stuck
        )
        msg = (
            f"Không lấy được dữ liệu {'/'.join(s.replace('_agent', '') for s in stuck)} "
            f"cho mã {plan.symbol} — có thể mã không hợp lệ hoặc nguồn dữ liệu đang lỗi."
            + (f" Chi tiết: {detail}" if detail.strip() else "")
        )
        trace.append(msg)
        return {
            **extra,
            "next_wave": "done",
            "stuck_turn": turn,
            "trace": trace,
            "draft": SynthOut(answer=msg, confidence=0.0),
        }

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
    """Duyệt toàn bộ pending còn `status=pending`, đọc lại DB để `db` phản ánh dữ liệu vừa COMMIT."""
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
    """Ưu tiên `draft` (SynthesisAgent); không có thì ghép câu tối thiểu từ price/news/db đã có."""
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

    usage = pop_usage(str(state.get("turn") or ""))
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
        prompt_tokens=int(usage["prompt_tokens"]) if usage else None,
        completion_tokens=int(usage["completion_tokens"]) if usage else None,
        cost_usd=round(usage["cost_usd"], 6) if usage else None,
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
    """Đọc long-term memory nếu có user_id; luôn ghi câu hỏi gốc vào `history` (kể cả không user_id)."""
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
    """LLM trích 1 sự thật dài hạn từ history gần đây; bỏ qua nếu không đáng lưu (worth_saving=False/"NONE")."""
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
        parsed, usage = chat_parsed_with_usage(
            bound_messages(
                "Trích sự thật DÀI HẠN về user từ hội thoại cổ phiếu. "
                "Chỉ mã theo dõi, khẩu vị rủi ro, quyết định đã chốt — không tóm giá/tin phiên.",
                lines,
            ),
            MemoryFact,
            DETERMINISTIC,
        )
        record_usage(str(state.get("turn") or ""), settings.llm_model, **usage)
    except Exception:
        return {}
    fact = (parsed.fact or "").strip()
    if parsed.worth_saving and fact and fact.upper() != "NONE":
        memory.save_to_long_term(user_id, fact)
    return {}
