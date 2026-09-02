"""Nodes hub — Supervisor hỏi LLM sau MỖI worker để chọn bước kế tiếp.

Cùng mẫu agent_m2 `hierarchical.py`: `supervisor_node` dùng
`with_structured_output(RoutingDecision)` chọn 1 trong
{price_agent, news_agent, db_agent, db_write, eval_agent, done}. Mỗi worker
chạy xong qua `_make_collect_node(domain)` gộp kết quả vào `notes[domain]`
rồi quay lại supervisor. Khi chọn "done" → `final_answer_node` (LLM tổng hợp
`notes` thành câu trả lời) → HITL (nếu còn pending) → reply.

Khác agent_m2: HITL không ở worker — hub dừng `interrupt_before=["hitl_commit"]`
trước khi COMMIT DB. `db_write` là 1 domain riêng (không phải mode ẩn) —
supervisor tự chọn khi thấy đã có price/news vừa crawl cần lưu.

`rewrite_question` (đầu graph): cùng ý `retriever._rewrite_query` — viết lại
câu user trước recall + routing; `question` gốc giữ cho history/eval.
"""

from __future__ import annotations

from datetime import date

from app.agent_pr import context, memory
from app.agent_pr.db_agent.nodes import approve_pending_write
from app.agent_pr.db_agent.schemas import Agent_Output as DbOut
from app.agent_pr.db_agent.schemas import PendingWrite
from app.agent_pr.news_agent.schemas import NewsItem
from app.agent_pr.supervisor_agent.schemas import (
    Agent_Output,
    FinalAnswer,
    MemoryFact,
    RewrittenQuery,
    RoutingDecision,
)
from app.agent_pr.supervisor_agent.state import SupervisorState
from app.config import settings
from app.llm.completion import chat_parsed_with_usage
from app.llm.params import DETERMINISTIC
from app.guardrails.injection import bound_messages
from app.monitoring.tracing import pop_usage, record_usage, step_parent, trace_step

_WORKER_DOMAINS = ["price_agent", "news_agent", "db_agent", "db_write", "eval_agent"]

# Cùng ý retriever._rewrite_query + ngày hiện tại (agent_m2 _system_prompt).
_REWRITE_SYSTEM = """Bạn là chuyên gia tìm kiếm thông tin cổ phiếu niêm yết Việt Nam.

Viết lại câu hỏi thành MỘT query rõ ràng để điều phối agent (giá vnstock, tin CafeF, lịch sử DB).
Giữ / tách mã CP nếu nhận ra (HPG, FPT, …). Làm rõ đại từ ("nó", "mã đó") từ hội thoại gần đây.
Không trả lời câu hỏi. Không bịa mã. Chỉ trả về câu đã viết lại, không giải thích."""

# Cùng ý _SUPERVISOR_SYSTEM agent_m2: worker không nói với nhau, supervisor chỉ chọn việc.
_SUPERVISOR_SYSTEM = """Bạn điều phối 4 worker chuyên biệt cho hỏi–đáp cổ phiếu niêm yết Việt Nam:

- price_agent: giá đóng cửa / % biến động so phiên trước (vnstock).
- news_agent: tin tức thô (CafeF).
- db_agent: đọc lịch sử đã lưu trong sqlite (chạy TRƯỚC khi crawl nếu câu cần giá/tin/lịch sử).
- eval_agent: chấm tin vs chiều giá — CHỈ chọn khi đã có CẢ price_agent lẫn news_agent chạy
  xong (xem notes), và câu hỏi thuộc 1 trong 3 dạng: hỏi NGUYÊN NHÂN biến động giá
  ("tại sao/vì sao ... tăng/giảm"), hỏi ĐỘ TIN CẬY/KHỚP của tin, hoặc hỏi CHẤM sentiment.
- db_write: soạn lệnh lưu dữ liệu VỪA crawl (không phải từ DB) vào kho — chỉ chọn khi
  notes đã có price_agent hoặc news_agent với dữ liệu MỚI (chưa lưu).

Worker KHÔNG tự giao tiếp với nhau — bạn quyết định worker nào chạy tiếp theo dựa trên
nhiệm vụ và ghi chú (notes) đã có. Không gọi lại worker đã có trong notes trừ khi cần làm mới.

Chọn 'done' khi đã đủ thông tin để trả lời user."""

_FINAL_ANSWER_SYSTEM = """Bạn tổng hợp ghi chú (notes) từ các worker cổ phiếu VN thành câu
trả lời cuối cho user — tiếng Việt, ngắn gọn, đầy đủ thông tin đã thu thập được.

Chỉ dùng dữ liệu có trong notes; không bịa số liệu/tin không có. Thiếu dữ liệu thì nói thiếu.
Hỏi tăng/giảm thì nêu chiều + % nếu notes có. Có kết quả db_write thì nhắc đã soạn lệnh chờ duyệt."""


def _query_for_routing(state: SupervisorState) -> str:
    """Câu dùng để routing/recall — ưu tiên bản đã rewrite, fallback câu gốc."""
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


def supervisor_node(state: SupervisorState) -> dict:
    """Hub. Hỏi LLM mỗi vòng: đã đủ thông tin theo `notes` chưa, worker nào tiếp theo."""

    def _supervisor(state: SupervisorState, question: str) -> tuple[str, str]:
        """Ghép prompt từ notes + memories rồi hỏi LLM routing. Trả (next_agent, reasoning)."""
        notes = dict(state.get("notes") or {})
        notes_text = "\n".join(f"[{d}] {n}" for d, n in notes.items()) or "(chưa có)"
        memories = list(state.get("memories") or [])
        parts = [f"Nhiệm vụ: {question}"]
        if memories:
            parts.append("Đã biết về user:\n" + "\n".join(f"- {m}" for m in memories))
        parts.append(f"Ghi chú từ worker đã chạy:\n{notes_text}")
        try:
            decision, usage = chat_parsed_with_usage(
                bound_messages(_SUPERVISOR_SYSTEM, "\n\n".join(parts)),
                RoutingDecision,
                DETERMINISTIC,
            )
            record_usage(str(state.get("turn") or ""), settings.llm_model, **usage)
            next_agent = decision.next_agent if decision.next_agent in [*_WORKER_DOMAINS, "done"] else "done"
            return next_agent, decision.reasoning
        except Exception as exc:
            return "done", f"Lỗi LLM routing: {exc}"

    question = str(state.get("rewritten_question") or state.get("question") or state.get("symbol") or "").strip()
    if not question:
        return {"next_agent": "done"}

    with trace_step(step_parent(state), "supervisor", input=question) as t:
        next_agent, reasoning = _supervisor(state, question)
        t["output"] = next_agent
        trace = list(state.get("trace") or []) + [f"Supervisor: {next_agent} · {reasoning}"]
        return {"next_agent": next_agent, "trace": trace}


def route_supervisor(state: SupervisorState) -> str:
    next_agent = state.get("next_agent") or "done"
    return next_agent if next_agent in _WORKER_DOMAINS else "final_answer"


def _news_candidates(news: object | None) -> list[dict]:
    """NewsItem → dict title/url cho stage_writes. Bỏ tin lấy từ DB."""
    if news is None or str(getattr(news, "source", "") or "") == "db":
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
    if price is None or str(getattr(price, "source", "") or "") == "db":
        return []
    last = float(getattr(price, "last", 0) or 0)
    trading_date = str(getattr(price, "trading_date", "") or "").strip()
    if last <= 0 or not trading_date:
        return []
    return [{"trading_date": trading_date, "close": last}]


def _make_collect_node(domain: str):
    """Chạy NGAY SAU subgraph của `domain` — gộp field kết quả (do subgraph
    vừa ghi) vào `notes[domain]` rồi quay lại supervisor. Cùng vai trò
    `_make_collect_node` agent_m2, khác chỗ đọc field trực tiếp (price/news/
    db/eval) thay vì `result` chung — mỗi worker agent_pr pack field riêng tên."""

    field_by_domain = {
        "price_agent": "price",
        "news_agent": "news",
        "db_agent": "db",
        "eval_agent": "eval",
    }

    def collect(state: SupervisorState) -> dict:
        field = field_by_domain[domain]
        value = state.get(field)
        summary = str(getattr(value, "detail", None) or value or "(không có kết quả)")
        notes = {**(state.get("notes") or {}), domain: summary}
        return {"notes": notes}

    return collect


def db_write(state: SupervisorState) -> dict:
    """Soạn lệnh ghi (pending, chưa COMMIT) từ dữ liệu price/news vừa crawl.

    Không phải worker ReAct riêng — gọi thẳng `db_agent` subgraph với
    mode="write" (cùng logic cũ), rồi gộp vào notes như collect node."""

    def _db_write(state: SupervisorState) -> dict:
        from app.agent_pr.db_agent.graph import db_agent as run_db_agent

        payload = {
            "symbol": str(state.get("symbol") or ""),
            "turn": str(state.get("turn") or ""),
            "mode": "write",
            "candidate_news": _news_candidates(state.get("news")),
            "candidate_prices": _price_candidates(state.get("price")),
        }
        db = run_db_agent(payload).get("db")
        notes = {**(state.get("notes") or {}), "db_write": str(getattr(db, "detail", None) or "(không có kết quả)")}
        return {"db": db, "notes": notes}

    with trace_step(step_parent(state), "db_write", input=str(state.get("symbol") or "")) as t:
        out = _db_write(state)
        t["output"] = out["notes"]["db_write"]
        return out


def hitl_commit(state: SupervisorState) -> dict:
    """Chạy sau interrupt_before — user đã đồng ý (hoặc còn lệnh pending chưa quyết).

    Duyệt lệnh status=pending. Lệnh user đã từ chối qua /pr/approve giữ rejected
    (approve_pending_write không đảo).
    """

    def _hitl_commit(state: SupervisorState) -> dict:
        db = state.get("db")
        pending = list(getattr(db, "pending_writes", None) or [])
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

    with trace_step(step_parent(state), "hitl_commit", input=str(state.get("symbol") or "")) as t:
        out = _hitl_commit(state)
        t["output"] = out.get("trace", [""])[-1] if out.get("trace") else ""
        return out


def _pending_list(db: object | None) -> list[PendingWrite]:
    return list(getattr(db, "pending_writes", None) or [])


def route_after_final_answer(state: SupervisorState) -> str:
    """Còn lệnh ghi đang chờ duyệt (và không bypass qua skip_hitl) → HITL trước reply."""
    skip_hitl = bool(state.get("skip_hitl"))
    if _pending_list(state.get("db")) and not skip_hitl:
        return "hitl_commit"
    return "reply"


def final_answer_node(state: SupervisorState) -> dict:
    """LLM tổng hợp `notes` thành câu trả lời cuối — cùng mẫu agent_m2 `final_answer_node`."""

    def _final_answer(state: SupervisorState, notes_text: str) -> str:
        symbol = str(state.get("symbol") or "")
        question = str(state.get("question") or "")
        try:
            parsed, usage = chat_parsed_with_usage(
                bound_messages(
                    _FINAL_ANSWER_SYSTEM,
                    f"Mã: {symbol or '(không rõ)'}\nNhiệm vụ: {question}\n\nGhi chú:\n{notes_text}",
                ),
                FinalAnswer,
                DETERMINISTIC,
            )
            record_usage(str(state.get("turn") or ""), settings.llm_model, **usage)
            return parsed.answer.strip()
        except Exception as exc:
            return f"Lỗi tổng hợp câu trả lời: {exc}. Ghi chú đã thu thập: {notes_text}"

    notes_text = "\n".join(f"[{d}] {n}" for d, n in (state.get("notes") or {}).items()) or "(chưa có ghi chú)"
    with trace_step(step_parent(state), "final_answer", input=str(state.get("question") or "")) as t:
        answer = _final_answer(state, notes_text)
        t["output"] = answer
        return {"final_answer": answer}


def reply(state: SupervisorState) -> dict:
    """Đóng gói `final_answer` (đã tổng hợp) thành Agent_Output trả user."""

    def _reply(state: SupervisorState) -> dict:
        symbol = str(state.get("symbol") or "")
        answer = str(state.get("final_answer") or "").strip() or "Không có đủ dữ liệu để trả lời."
        db = state.get("db")
        if db and str(db.detail or "").startswith("HITL:"):
            answer = answer.rstrip() + " " + db.detail

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
            prompt_tokens=int(usage["prompt_tokens"]) if usage else None,
            completion_tokens=int(usage["completion_tokens"]) if usage else None,
            cost_usd=round(usage["cost_usd"], 6) if usage else None,
        )
        return {
            "output": output,
            "history": [{"role": "assistant", "content": output.answer}],
        }

    with trace_step(step_parent(state), "reply", input=str(state.get("question") or "")) as t:
        out = _reply(state)
        output = out.get("output")
        t["output"] = getattr(output, "answer", None)
        return out


def compact_history(state: SupervisorState) -> dict:
    """Chỉ chạy khi should_compact_route chọn node này (>40% window)."""
    history = list(state.get("history") or [])
    compacted = context.summarize_old_messages(
        history, settings.agent_keep_recent_messages
    )
    return {"history": context.set_history(compacted)}


def should_compact_route(state: SupervisorState) -> str:
    """Nguyên tắc 40–60%: vượt 40% window → compact; không thì thẳng supervisor."""
    history = list(state.get("history") or [])
    if context.should_compact(history, settings.agent_context_window_tokens):
        return "compact_history"
    return "supervisor"


def recall_memory(state: SupervisorState) -> dict:
    """Đầu lượt: đọc long-term (Qdrant user_memory) theo user_id. Không user → bỏ qua."""

    def _recall_memory(state: SupervisorState) -> dict:
        user_id = str(state.get("user_id") or "").strip()
        original = str(state.get("question") or "")
        query = _query_for_routing(state) or original
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

    with trace_step(step_parent(state), "recall_memory", input=str(state.get("user_id") or "")) as t:
        out = _recall_memory(state)
        t["output"] = {"n_memories": len(out.get("memories") or [])}
        return out


def store_memory(state: SupervisorState) -> dict:
    """Cuối lượt: trích 1 sự thật dài hạn (nếu có) rồi ghi Qdrant. Không user → bỏ qua."""
    user_id = str(state.get("user_id") or "").strip()
    if not user_id:
        return {}

    def _store_memory(state: SupervisorState) -> dict:
        output = state.get("output")
        answer = str(getattr(output, "answer", None) or "")
        question = str(state.get("question") or "")
        if not question or not answer:
            return {}
        try:
            parsed, usage = chat_parsed_with_usage(
                bound_messages(
                    "Trích 1 sự thật đáng nhớ dài hạn về user (mã theo dõi, khẩu vị, thói quen "
                    "hỏi) từ đoạn hội thoại sau, nếu có. Không bịa.",
                    f"Câu hỏi: {question}\nTrả lời: {answer}",
                ),
                MemoryFact,
                DETERMINISTIC,
            )
            record_usage(str(state.get("turn") or ""), settings.llm_model, **usage)
        except Exception:
            return {}
        if parsed.worth_saving and parsed.fact.strip():
            try:
                memory.save_to_long_term(user_id, parsed.fact.strip())
            except Exception:
                pass
        return {}

    with trace_step(step_parent(state), "store_memory", input=user_id) as t:
        out = _store_memory(state)
        t["output"] = "saved" if out else "skip"
        return out
