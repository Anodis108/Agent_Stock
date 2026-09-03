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
Giữ / tách mã CP nếu nhận ra (HPG, FPT, …). Nếu câu hỏi nhắc đến NHIỀU mã (so sánh, liệt kê),
liệt kê TẤT CẢ vào symbols — đừng chỉ lấy 1 mã. Giữ nguyên là MỘT câu hỏi, không tách thành
nhiều câu. Làm rõ đại từ ("nó", "mã đó") từ hội thoại gần đây.
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
nhiệm vụ, hội thoại gần đây và ghi chú (notes) đã có. Không gọi lại worker đã có trong
notes trừ khi cần làm mới.

Nếu nhiệm vụ có NHIỀU mã (vd so sánh HPG và FPT), mỗi lượt gọi worker BẮT BUỘC trả về
`symbol` cụ thể (đúng 1 mã trong danh sách "Các mã cần xử lý") — gọi TỪNG MÃ MỘT, không
gộp nhiều mã vào 1 lượt gọi. Ghi chú (notes) nhóm theo TỪNG MÃ — xem để biết mã nào còn
thiếu worker nào. Chỉ chọn 'done' khi TẤT CẢ mã đã đủ thông tin cần thiết.

Ghi chú của db_agent có kèm ĐỘ MỚI dữ liệu (vd "5 phút trước", "hơn 1 giờ trước"). Nếu dữ
liệu trong DB mới hơn khoảng {freshness_minutes} phút, coi là ĐỦ DÙNG — KHÔNG cần gọi lại
price_agent/news_agent để crawl lại cùng mã. Chỉ crawl lại khi DB chưa có dữ liệu, dữ liệu
đã quá cũ (hơn vài giờ), hoặc user yêu cầu rõ "mới nhất/cập nhật lại".

Câu hỏi về CHÍNH hội thoại (vd. "vừa rồi tôi hỏi gì", "mã nào tôi hỏi lúc nãy") — trả lời
được ngay từ "Hội thoại gần đây" bên dưới, không cần gọi worker nào, chọn 'done' luôn.

Chọn 'done' khi đã đủ thông tin (từ notes hoặc hội thoại gần đây) để trả lời user."""

_FINAL_ANSWER_SYSTEM = """Bạn tổng hợp ghi chú (notes) từ các worker cổ phiếu VN thành câu
trả lời cuối cho user — tiếng Việt, ngắn gọn, đầy đủ thông tin đã thu thập được.

Chỉ dùng dữ liệu có trong notes hoặc hội thoại gần đây; không bịa số liệu/tin không có.
Thiếu dữ liệu thì nói thiếu. Hỏi tăng/giảm thì nêu chiều + % nếu notes có. Có kết quả
db_write thì nhắc đã soạn lệnh chờ duyệt. Câu hỏi về CHÍNH hội thoại (vd. "vừa hỏi mã
nào") thì trả lời thẳng từ "Hội thoại gần đây", không nói "chưa có dữ liệu"."""


def rewrite_question(state: SupervisorState) -> dict:
    """Viết lại câu hỏi — cùng kiểu retriever._rewrite_query. Giữ `question` gốc."""
    original = str(state.get("question") or "").strip()
    with trace_step(step_parent(state), "rewrite_question", input=original) as t:
        rewritten = original
        extra_symbols: list[str] = []
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
                extra_symbols = parsed.symbols
            except Exception:
                rewritten = original
                extra_symbols = []
        t["output"] = rewritten or "skip"
        out: dict = {"rewritten_question": rewritten}
        existing_symbols = list(state.get("symbols") or ([state["symbol"]] if state.get("symbol") else []))
        if extra_symbols and not existing_symbols:
            out["symbols"] = extra_symbols
            out["symbol"] = extra_symbols[0]
        if rewritten and rewritten != original:
            out["trace"] = list(state.get("trace") or []) + [f"Rewrite: {rewritten}"]
        return out


_LOOP_WINDOW = 3  # PDF gợi ý 4 (tool_calls); ở đây giảm còn 3 — mỗi vòng routing
                  # tốn ~2-3 bước graph (agent+collect / supervisor+db_write) nên
                  # cần bắt lặp SỚM hơn để còn đủ ngân sách recursion_limit=28


def _looping(history: list[str], window: int = _LOOP_WINDOW) -> bool:
    """detect_repetition (Bài 10 P3) áp cho routing thay vì tool_calls: N lựa
    chọn next_agent gần nhất giống hệt nhau → agent bị kẹt, chưa hẳn tiến bộ."""
    recent = history[-window:]
    return len(recent) >= window and len(set(recent)) == 1


def supervisor_node(state: SupervisorState) -> dict:
    """Hub. Hỏi LLM mỗi vòng: đã đủ thông tin theo `notes` chưa, worker nào tiếp theo.

    Loop Detection (Bài 10 P3, detect_repetition) chạy TRƯỚC khi gọi LLM: đã
    lặp đủ window (4 lần liên tiếp giống hệt) → ép "done" ngay, không gọi LLM
    thêm — mỗi vòng supervisor→worker→collect tốn ~2-3 bước graph, "cảnh báo
    rồi thử lại" (chèn system message, đợi vòng sau) vẫn tốn đủ bước để chạm
    recursion_limit=28 trước khi guard kịp chặn lần 2 (bug đã tái hiện thật).
    Đơn giản & rẻ hơn: chặn cứng ngay tại điểm phát hiện.
    """

    def _supervisor(state: SupervisorState, question: str, symbols: list[str]) -> tuple[str, str, str]:
        """Ghép prompt từ history + notes + memories rồi hỏi LLM routing.

        Trả (next_agent, reasoning, chosen_symbol) — `chosen_symbol` là mã worker
        vòng này sẽ xử lý (rỗng khi next_agent="done" hoặc câu hỏi chỉ 1 mã)."""
        notes = {sym: dict(doms) for sym, doms in (state.get("notes") or {}).items()}
        notes_text = "\n".join(
            f"[{sym}][{d}] {n}" for sym, doms in notes.items() for d, n in doms.items()
        ) or "(chưa có)"
        memories = list(state.get("memories") or [])
        history = list(state.get("history") or [])
        parts = [f"Nhiệm vụ: {question}", f"Các mã cần xử lý: {', '.join(symbols) or '(chưa rõ)'}"]
        if history:
            shaped = context.sliding_window(history, settings.agent_keep_recent_messages)
            parts.append("Hội thoại gần đây (các lượt trước):\n" + context.format_messages(shaped))
        if memories:
            parts.append("Đã biết về user:\n" + "\n".join(f"- {m}" for m in memories))
        parts.append(f"Ghi chú từ worker đã chạy lượt này:\n{notes_text}")
        system = _SUPERVISOR_SYSTEM.format(freshness_minutes=settings.agent_pr_freshness_minutes)
        try:
            decision, usage = chat_parsed_with_usage(
                bound_messages(system, "\n\n".join(parts)),
                RoutingDecision,
                DETERMINISTIC,
            )
            record_usage(str(state.get("turn") or ""), settings.llm_model, **usage)
            next_agent = decision.next_agent if decision.next_agent in [*_WORKER_DOMAINS, "done"] else "done"
            chosen_symbol = (decision.symbol or "").strip().upper()
            if next_agent in _WORKER_DOMAINS and not chosen_symbol:
                if len(symbols) == 1:
                    chosen_symbol = symbols[0]
                else:
                    # LLM quên trả symbol khi có nhiều mã — fallback quyết định: mã
                    # đầu tiên còn thiếu domain đó trong notes, tránh crash/kẹt vòng lặp.
                    domain = next_agent
                    chosen_symbol = next(
                        (sym for sym in symbols if domain not in notes.get(sym, {})),
                        symbols[0] if symbols else "",
                    )
            return next_agent, decision.reasoning, chosen_symbol
        except Exception as exc:
            return "done", f"Lỗi LLM routing: {exc}", ""

    symbols = list(state.get("symbols") or ([state["symbol"]] if state.get("symbol") else []))
    question = str(state.get("rewritten_question") or state.get("question") or state.get("symbol") or "").strip()
    if not question:
        return {"next_agent": "done"}

    agent_history = list(state.get("agent_history") or [])

    with trace_step(step_parent(state), "supervisor", input=question) as t:
        if _looping(agent_history):
            # KHÔNG xoá agent_history: route_supervisor có thể vẫn đưa graph
            # qua db_write (ghi dữ liệu vừa crawl) rồi quay lại đây — nếu xoá,
            # bộ đếm "quên" ngay lần ép đầu tiên và LLM có thể chọn lại đúng
            # domain đã lặp, phải tích đủ window lần nữa mới chặn tiếp.
            next_agent = "done"
            reasoning = f"Dừng ép buộc — lặp lại '{agent_history[-1]}' {_LOOP_WINDOW} lần liên tiếp."
            chosen_symbol = ""
            next_history = agent_history
        else:
            next_agent, reasoning, chosen_symbol = _supervisor(state, question, symbols)
            entry = f"{chosen_symbol}:{next_agent}" if chosen_symbol else next_agent
            next_history = (agent_history + [entry])[-_LOOP_WINDOW:] if next_agent != "done" else agent_history

        t["output"] = {
            "next_agent": next_agent,
            "symbol": chosen_symbol,
            "reasoning": reasoning,
            "agent_history": agent_history,  # window trước khi route vòng này — để soi Langfuse thấy đúng chuỗi dẫn tới lặp
            "loop_forced": _looping(agent_history),
        }
        trace = list(state.get("trace") or []) + [f"Supervisor: {next_agent} · {reasoning}"]
        out: dict = {"next_agent": next_agent, "agent_history": next_history, "trace": trace}
        if chosen_symbol:
            out["symbol"] = chosen_symbol
        return out


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


def route_supervisor(state: SupervisorState) -> str:
    """Map `next_agent` → node. Code-enforced: LLM chọn "done" nhưng còn dữ
    liệu vừa crawl (chưa soạn ghi) — ở BẤT KỲ mã nào — ép qua `db_write` trước,
    không phụ thuộc LLM có nhớ tự chọn hay không — side-effect ghi DB không
    được phó mặc cho routing tự do (khác chọn worker đọc, vốn không side-effect)."""
    next_agent = state.get("next_agent") or "done"
    if next_agent in _WORKER_DOMAINS:
        return next_agent
    notes = state.get("notes") or {}
    symbols = list(state.get("symbols") or ([state["symbol"]] if state.get("symbol") else []))
    news_map = state.get("news") or {}
    price_map = state.get("price") or {}
    needs_write = any(
        "db_write" not in notes.get(sym, {})
        and (_news_candidates(news_map.get(sym)) or _price_candidates(price_map.get(sym)))
        for sym in symbols
    )
    if needs_write:
        return "db_write"
    return "final_answer"


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

    def _summarize(field: str, value) -> str:
        """price/news không có field `detail` (chỉ db/eval có) — dựng câu tóm
        tắt riêng, tránh in repr Pydantic thô vào notes/trace."""
        if value is None:
            return "(không có kết quả)"
        detail = getattr(value, "detail", None)
        if detail:
            return str(detail)
        if field == "price":
            if not getattr(value, "last", 0):
                return f"{value.symbol}: không lấy được giá ({value.source})."
            pct = value.pct_change
            pct_text = f", {'giảm' if pct < 0 else 'tăng'} {abs(pct):.1f}%" if pct is not None else ""
            return f"{value.symbol}: {value.last:,.0f} VND{pct_text} ({value.source})."
        if field == "news":
            n = len(value.articles or [])
            return f"{value.symbol}: {n} tin ({value.source})." if n else f"{value.symbol}: chưa tìm thấy tin ({value.source})."
        return str(value)

    def collect(state: SupervisorState) -> dict:
        field = field_by_domain[domain]
        symbol = str(state.get("symbol") or "")
        value = dict(state.get(field) or {}).get(symbol)
        summary = _summarize(field, value)
        notes = {sym: dict(doms) for sym, doms in (state.get("notes") or {}).items()}
        notes.setdefault(symbol, {})[domain] = summary
        trace = list(state.get("trace") or []) + [f"[{symbol}] {domain}: {summary}"]
        return {"notes": notes, "trace": trace}

    return collect


def db_write(state: SupervisorState) -> dict:
    """Soạn lệnh ghi (pending, chưa COMMIT) từ dữ liệu price/news vừa crawl.

    Không phải worker ReAct riêng — gọi thẳng `db_agent` subgraph với
    mode="write" (cùng logic cũ), rồi gộp vào notes như collect node. Lặp qua
    TẤT CẢ mã có candidate chưa ghi trong 1 lần chạy node — route_supervisor
    không tự chọn được symbol cho nhánh này (hàm string thuần), và loop nội bộ
    ở đây rẻ hơn tốn thêm 1 vòng supervisor riêng cho mỗi mã."""

    def _db_write(state: SupervisorState) -> dict:
        # Gọi THẲNG subgraph con của db_agent (không phải wrapper hub db_agent()
        # ở graph.py) — wrapper hub giờ trả `db` đã merge thành dict[symbol,DbOut],
        # còn ở đây cần đúng 1 DbOut cho từng symbol trong vòng lặp.
        from app.agent_pr.db_agent.graph import _build_graph as _build_db_graph

        symbols = list(state.get("symbols") or ([state["symbol"]] if state.get("symbol") else []))
        news_map = dict(state.get("news") or {})
        price_map = dict(state.get("price") or {})
        db_map = dict(state.get("db") or {})
        notes = {sym: dict(doms) for sym, doms in (state.get("notes") or {}).items()}
        trace = list(state.get("trace") or [])
        for sym in symbols:
            news_cands = _news_candidates(news_map.get(sym))
            price_cands = _price_candidates(price_map.get(sym))
            if not news_cands and not price_cands:
                continue
            payload = {
                "symbol": sym,
                "turn": str(state.get("turn") or ""),
                "mode": "write",
                "candidate_news": news_cands,
                "candidate_prices": price_cands,
            }
            db = _build_db_graph().invoke(payload).get("db")
            db_map[sym] = db
            summary = str(getattr(db, "detail", None) or "(không có kết quả)")
            notes.setdefault(sym, {})["db_write"] = summary
            trace.append(f"db_write[{sym}]: {summary}")
        return {"db": db_map, "notes": notes, "trace": trace}

    with trace_step(step_parent(state), "db_write", input=str(state.get("symbol") or "")) as t:
        out = _db_write(state)
        t["output"] = out["trace"][-1] if out["trace"] else ""
        return out


def hitl_commit(state: SupervisorState) -> dict:
    """Chạy sau interrupt_before — user đã đồng ý (hoặc còn lệnh pending chưa quyết).

    Duyệt lệnh status=pending. Lệnh user đã từ chối qua /pr/approve giữ rejected
    (approve_pending_write không đảo).
    """

    def _hitl_commit(state: SupervisorState) -> dict:
        from app.agent_pr.db_agent.nodes import _read_rows
        from app.agent_pr.db_agent.schemas import PriceRow, SavedNews

        db_map = dict(state.get("db") or {})
        trace = list(state.get("trace") or [])
        for sym, db in db_map.items():
            pending = list(getattr(db, "pending_writes", None) or [])
            n_ok = 0
            for pw in pending:
                try:
                    if approve_pending_write(pw.id, approve=True, kind=pw.kind or "news"):
                        n_ok += 1
                except Exception:
                    continue
            rows = _read_rows(sym) if sym else {"price_rows": [], "news_rows": []}
            refreshed = DbOut(
                symbol=sym,
                price_history=[PriceRow(**row) for row in rows["price_rows"]],
                saved_news=[SavedNews(**row) for row in rows["news_rows"]],
                pending_writes=[],
                detail=f"HITL: đã COMMIT {n_ok} lệnh vào DB",
            )
            db_map[sym] = refreshed
            trace.append(f"[{sym}] {refreshed.detail}")
        return {"db": db_map, "trace": trace}

    with trace_step(step_parent(state), "hitl_commit", input=str(state.get("symbol") or "")) as t:
        out = _hitl_commit(state)
        t["output"] = out.get("trace", [""])[-1] if out.get("trace") else ""
        return out


def route_after_final_answer(state: SupervisorState) -> str:
    """Còn lệnh ghi đang chờ duyệt (ở BẤT KỲ mã nào) và không bypass qua skip_hitl → HITL trước reply."""

    def _pending_list(db: object | None) -> list[PendingWrite]:
        return list(getattr(db, "pending_writes", None) or [])

    skip_hitl = bool(state.get("skip_hitl"))
    db_map = state.get("db") or {}
    has_pending = any(_pending_list(db) for db in db_map.values())
    if has_pending and not skip_hitl:
        return "hitl_commit"
    return "reply"


_HARD_FINAL_ANSWER_KEYWORDS = (
    "so sánh", "tại sao", "vì sao", "phân tích", "đánh giá", "nên mua", "nên bán",
)


def _select_final_answer_model(state: SupervisorState) -> str:
    """Model Routing (Bài 8 Phần 4) riêng cho final_answer — không tái dùng thẳng
    `rule_based_router` (heuristic word-count/code-block của nó không hợp câu
    hỏi tiếng Việt ngắn nhưng phức tạp, vd so sánh 2 mã). gpt-4o khi: nhiều mã,
    câu hỏi so sánh/nguyên nhân/khuyến nghị, hoặc notes có ≥3 domain (tổng hợp
    phức tạp) — còn lại giữ gpt-4o-mini (rẻ, đủ cho câu đơn giản)."""
    from app.optimization.routing import rule_based_router

    symbols = list(state.get("symbols") or ([state["symbol"]] if state.get("symbol") else []))
    notes = state.get("notes") or {}
    question = str(state.get("rewritten_question") or state.get("question") or "").lower()
    n_domains = len({d for sym_notes in notes.values() for d in sym_notes})
    if len(symbols) >= 2:
        return "gpt-4o"
    if any(kw in question for kw in _HARD_FINAL_ANSWER_KEYWORDS):
        return "gpt-4o"
    if n_domains >= 3:
        return "gpt-4o"
    if question and rule_based_router(question) == "gpt-4o":
        return "gpt-4o"
    return "gpt-4o-mini"


def final_answer_node(state: SupervisorState) -> dict:
    """LLM tổng hợp `notes` thành câu trả lời cuối — cùng mẫu agent_m2 `final_answer_node`."""

    def _final_answer(state: SupervisorState, notes_text: str) -> str:
        symbols = list(state.get("symbols") or ([state["symbol"]] if state.get("symbol") else []))
        question = str(state.get("question") or "")
        history = list(state.get("history") or [])
        parts = [f"Mã: {', '.join(symbols) or '(không rõ)'}", f"Nhiệm vụ: {question}"]
        if history:
            shaped = context.sliding_window(history, settings.agent_keep_recent_messages)
            parts.append("Hội thoại gần đây (các lượt trước):\n" + context.format_messages(shaped))
        parts.append(f"Ghi chú:\n{notes_text}")
        model = _select_final_answer_model(state)
        try:
            parsed, usage = chat_parsed_with_usage(
                bound_messages(_FINAL_ANSWER_SYSTEM, "\n\n".join(parts)),
                FinalAnswer,
                DETERMINISTIC,
                model=model,
            )
            record_usage(str(state.get("turn") or ""), model, **usage)
            return parsed.answer.strip()
        except Exception as exc:
            return f"Lỗi tổng hợp câu trả lời: {exc}. Ghi chú đã thu thập: {notes_text}"

    notes = {sym: dict(doms) for sym, doms in (state.get("notes") or {}).items()}
    notes_text = "\n".join(
        f"[{sym}][{d}] {n}" for sym, doms in notes.items() for d, n in doms.items()
    ) or "(chưa có ghi chú)"
    with trace_step(step_parent(state), "final_answer", input=str(state.get("question") or "")) as t:
        answer = _final_answer(state, notes_text)
        t["output"] = answer
        return {"final_answer": answer}


def reply(state: SupervisorState) -> dict:
    """Đóng gói `final_answer` (đã tổng hợp) thành Agent_Output trả user."""

    def _reply(state: SupervisorState) -> dict:
        symbols = list(state.get("symbols") or ([state["symbol"]] if state.get("symbol") else []))
        symbol0 = symbols[0] if symbols else str(state.get("symbol") or "")
        answer = str(state.get("final_answer") or "").strip() or "Không có đủ dữ liệu để trả lời."
        db_map = dict(state.get("db") or {})
        db0 = db_map.get(symbol0)
        if any(str(getattr(db, "detail", "") or "").startswith("HITL:") for db in db_map.values()):
            hitl_lines = [db.detail for db in db_map.values() if str(db.detail or "").startswith("HITL:")]
            answer = answer.rstrip() + " " + " ".join(hitl_lines)

        usage = pop_usage(str(state.get("turn") or ""))
        trace = list(state.get("trace") or [])
        if usage:
            trace.append(
                f"Token: {int(usage['prompt_tokens'])} in + {int(usage['completion_tokens'])} out"
                f" (~${usage['cost_usd']:.6f})"
            )
        price_map = dict(state.get("price") or {})
        news_map = dict(state.get("news") or {})
        eval_map = dict(state.get("eval") or {})
        output = Agent_Output(
            symbol=symbol0,
            symbols=symbols,
            question=str(state.get("question") or ""),
            answer=answer,
            price=price_map.get(symbol0),
            news=news_map.get(symbol0),
            eval=eval_map.get(symbol0),
            db=db0,
            price_by_symbol=price_map,
            news_by_symbol=news_map,
            eval_by_symbol=eval_map,
            db_by_symbol=db_map,
            trace=trace,
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

    def _query_for_routing(state: SupervisorState) -> str:
        """Câu dùng để recall — ưu tiên bản đã rewrite, fallback câu gốc."""
        return str(state.get("rewritten_question") or state.get("question") or "").strip()

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
