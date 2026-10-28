"""Node riêng của team chat (agent = subgraph make_agent_graph ở graph.py — tool + state ở <agent>/).

  1. Điểm vào team — guardrail_input (+ route_after_guardrail), rewrite_question (LLM → task cho chat_supervisor)
  2. Worker node    — scan_team (nhờ team scan thu thập dữ liệu), portfolio_watch (bảng NAV / watchlist), concept_retrieval (RAG)
                      → ghi `result` cho notes như agent
  3. Memory dài hạn — recall_memory (rewrite_question gọi) / store_memory (save_long_term_memory gọi) — hàm, không phải node
  4. Trả lời        — answer (final_answer: task + notes, stream) → save_long_term_memory
                      (tạm bỏ guardrail_output)
"""

from __future__ import annotations

import json
import re
from typing import Any

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from langgraph.config import get_stream_writer
from langgraph.runtime import get_runtime

from ai_backend.domain.guardrails import check_input_guardrail
from ai_backend.domain.agents.chat.state import ChatTeamState, RewrittenQuestion
from ai_backend.domain.agents.scan.graph import build_graph as build_scan_graph
from ai_backend.infra.llm.completion import chat_stream
from ai_backend.infra.llm.params import DETERMINISTIC
from ai_backend.infra.llm.structured import call_llm_structured
from ai_backend.infra.monitoring.tracing import trace_step, trace_stream
from ai_backend.infra.prompts import registry
from ai_backend.infra.storage.long_term_memory import recall_long_term, save_to_long_term
from ai_backend.shared.logging import get_logger
from common.settings import settings
from common.domain.entities import WatchlistItem
from common.transport.schemas import MemoryFact, RewriteOutput

_logger = get_logger(__name__)


# ── 1. Điểm vào team chat ────────────────────────────────────────────────────


def guardrail_input_node(state: ChatTeamState, config: RunnableConfig) -> dict:
    """Nạp câu hỏi (HumanMessage cuối) + guardrail đầu vào: chặn prompt injection / ngoài phạm vi; nhận diện câu chào."""
    from ai_backend.infra.cache.semantic import clear_semantic_question

    clear_semantic_question()  # đầu lượt: xoá câu hỏi semantic cache của lượt trước
    q = str(state["messages"][-1].content)
    res = check_input_guardrail(q)
    with trace_step(get_runtime().context["trace_span"], "guardrail_input", input=q) as box:
        box["output"] = {"is_safe": res.is_safe, "category": res.category, "reason": res.reason}
    # rewritten / db_results: node sau đọc thẳng state[...] kể cả khi rewrite / db_agent không chạy
    return {"question": q, "guardrail_result": res, "rewritten": None, "db_results": None}


def route_after_guardrail(state: ChatTeamState) -> str:
    """Vi phạm hoặc câu chào → answer trả thẳng; còn lại → rewrite_question."""
    res = state["guardrail_result"]
    return "answer" if res and (not res.is_safe or res.category == "greeting") else "rewrite_question"


async def rewrite_node(state: ChatTeamState, config: RunnableConfig) -> dict:
    """LLM viết lại câu hỏi (phân giải đại từ từ hội thoại ngắn hạn, trích mã) → rewritten + symbols + task cho chat_supervisor.

    Chỉ chạy khi guardrail cho qua → đọc hội thoại + recall memory dài hạn ở đây (câu bị chặn / chào không cần).
    """
    from ai_backend.infra.cache.exact import llm_cache_scope
    from ai_backend.infra.cache.semantic import set_semantic_question

    from ai_backend.infra.storage.memory_store import apply_sliding_window_with_ttl_eviction

    q = state["question"] or ""
    uid = str(state["user_id"] or "").strip()
    memory_store = get_runtime().context["memory_store"]
    limit, ttl = settings.memory_short_term_window, settings.memory_short_term_ttl_minutes
    conversation = memory_store.list_conversation(uid, limit=limit, ttl_minutes=ttl) if memory_store else []
    conversation = apply_sliding_window_with_ttl_eviction(conversation, limit=limit, ttl_minutes=ttl)
    memories = recall_memory(uid, q)
    prompt = registry().render("rewrite_question", question=q, conversation=json.dumps(conversation, ensure_ascii=False))
    with trace_step(get_runtime().context["trace_span"], "rewrite_question", input=q) as box:
        try:
            with llm_cache_scope(prompt_name="rewrite_question", prompt_version="production", normalized_question=q):
                out = call_llm_structured(
                    [{"role": "user", "content": prompt}], RewriteOutput, params=DETERMINISTIC, max_retries=1
                )
        except Exception as exc:  # noqa: BLE001 — LLM lỗi: giữ nguyên câu hỏi
            _logger.warning("rewrite_question: LLM lỗi (%s) → giữ câu gốc", exc)
            out = RewriteOutput(rewritten=q)
        symbols = list(dict.fromkeys(s.upper() for s in [out.symbol, *out.symbols] if s))
        rewritten = RewrittenQuestion(
            original=q,
            rewritten=out.rewritten or q,
            intent=out.intent,
            symbols=symbols,
            sub_questions=out.sub_questions or [q],
        )
        set_semantic_question(rewritten.rewritten)
        box["output"] = {"rewritten": rewritten.rewritten, "symbols": symbols, "intent": rewritten.intent}

    task = (
        f"Câu hỏi người dùng: {rewritten.rewritten}\n"
        f"Mã cổ phiếu: {', '.join(symbols) or '(không có)'}\n"
        f"Ghi nhớ dài hạn về người dùng: {'; '.join(memories) or '(không có)'}"
    )
    return {"rewritten": rewritten, "symbols": symbols, "memories": memories, "task": task, "notes": {}}


# ── 2. Worker node (không phải agent: không tool, không vòng LLM) ────────────


async def scan_team_node(state: ChatTeamState, config: RunnableConfig) -> dict:
    """Nhờ team scan thu thập dữ liệu — scan_supervisor (LLM) tự chọn price / news / eval / db_agent theo task.

    Bọc trong node (không nhúng thẳng): chat chỉ nhận dữ liệu + tóm tắt `result`, không biết worker bên trong scan.
    """
    task = f"Thu thập dữ liệu để trả lời câu hỏi (KHÔNG quét cảnh báo, không soạn cảnh báo).\n{state['task']}"
    out = await build_scan_graph().ainvoke({"prices": [], "news": [], "eval_result": None, **state, "task": task, "notes": {}}, config)
    update = {k: out[k] for k in ("prices", "news", "eval_result", "db_results", "error") if k in out}
    update["result"] = "\n".join(f"[{w}] {n}" for w, n in (out["notes"] or {}).items()) or "(không thu thập được dữ liệu)"
    return update


def portfolio_watch_node(state: ChatTeamState, config: RunnableConfig) -> dict:
    """db_results (scan_team / db_agent đã đọc) → bảng NAV / P&L danh mục + watchlist (markdown answer trả thẳng)."""

    def holdings_summary(holdings: list[dict[str, Any]], price_source: Any) -> dict[str, Any]:
        """Tính NAV / P&L. Giá < 1000 coi là nghìn VND (giá vnstock) → nhân 1000. Không lấy được giá → P&L = 0."""
        items = []
        total_cost = total_nav = 0.0
        for row in holdings:
            symbol = str(row["symbol"]).upper()
            qty = int(row["quantity"])
            buy = float(row["avg_buy_price"])
            cost = qty * (buy * 1000 if 0 < buy < 1000 else buy)
            current = None
            try:
                current = price_source.fetch_latest_close(symbol).latest_close
            except Exception:  # noqa: BLE001 — thiếu giá: giữ giá vốn
                pass
            value = qty * (current * 1000 if 0 < current < 1000 else current) if current else cost
            pnl = value - cost
            items.append({
                "symbol": symbol,
                "quantity": qty,
                "avg_buy_price": buy,
                "current_price": current,
                "cost_basis": cost,
                "unrealized_pnl": pnl,
                "pnl_pct": pnl / cost * 100 if cost else 0.0,
            })
            total_cost += cost
            total_nav += value
        total_pnl = total_nav - total_cost
        return {
            "items": items,
            "total_nav": total_nav,
            "total_cost": total_cost,
            "total_unrealized_pnl": total_pnl,
            "total_pnl_pct": total_pnl / total_cost * 100 if total_cost else 0.0,
        }

    def format_portfolio_markdown(summary: dict[str, Any], user_id: str) -> str:
        pnl, pct = summary["total_unrealized_pnl"], summary["total_pnl_pct"]
        lines = [
            f"### 💼 Báo Cáo Hiệu Suất Danh Mục Đầu Tư (Tài khoản: `{user_id}`)\n",
            f"- **Tổng giá trị tài sản (NAV)**: **{summary['total_nav']:,.0f} VND**",
            f"- **Tổng vốn đầu tư**: **{summary['total_cost']:,.0f} VND**",
            f"- **Lãi/Lỗ tạm tính (P&L)**: **{pnl:+,.0f} VND** ({pct:+.2f}%)\n",
        ]
        if not summary["items"]:
            lines.append(
                "> ℹ️ **Danh mục hiện chưa có cổ phiếu nào.**\n"
                "> Bạn có thể thêm cổ phiếu vào danh mục để hệ thống tự động theo dõi thị giá và lãi/lỗ theo thời gian thực."
            )
            return "\n".join(lines)
        lines.append("| Mã CP | Khối lượng | Giá vốn (nghìn VNĐ) | Thị giá (nghìn VNĐ) | Lãi/Lỗ (VND) | Tỷ suất sinh lời |")
        lines.append("| :--- | :---: | :---: | :---: | :---: | :---: |")
        for it in summary["items"]:
            current = f"{it['current_price']:,.1f}" if it["current_price"] is not None else "Đang cập nhật"
            lines.append(
                f"| **{it['symbol']}** | {it['quantity']:,} | {it['avg_buy_price']:,.1f} | {current} "
                f"| {it['unrealized_pnl']:+,.0f} | {it['pnl_pct']:+.2f}% |"
            )
        return "\n".join(lines)

    def format_watchlist_markdown(items: list[WatchlistItem], user_id: str) -> str:
        lines = [f"### 📋 Danh Sách Theo Dõi & Ngưỡng Cảnh Báo (Watchlist - `{user_id}`)\n"]
        if not items:
            lines.append(
                "> ℹ️ **Danh sách theo dõi của bạn hiện đang trống.**\n"
                "> Bạn có thể thêm các mã cổ phiếu quan tâm vào Watchlist và thiết lập ngưỡng cảnh báo biến động "
                "(ví dụ: ±3% hoặc ±5%) để nhận thông báo kịp thời."
            )
            return "\n".join(lines)
        lines.append("| STT | Mã cổ phiếu | Ngưỡng cảnh báo biến động | Trạng thái giám sát |")
        lines.append("| :---: | :--- | :---: | :---: |")
        for idx, it in enumerate(items, 1):
            lines.append(f"| {idx} | **{it.symbol}** | ±{it.threshold_pct:.1f}% | Đang theo dõi |")
        lines.append(f"\n*Tổng cộng: **{len(items)}** mã trong danh sách theo dõi.*")
        return "\n".join(lines)

    user_id = state["user_id"] or "default"
    db = state["db_results"]
    with trace_step(get_runtime().context["trace_span"], "portfolio_watch", input=user_id) as box:
        summary, watchlist, parts = None, [], []
        error = db.error if db else "chưa có dữ liệu DB (scan_team / db_agent chưa chạy)"
        if db:
            summary = holdings_summary(db.holdings, get_runtime().context["price_source"])
            watchlist = [
                WatchlistItem(
                    user_id=str(w["user_id"] or user_id),
                    symbol=str(w["symbol"]).strip().upper(),
                    threshold_pct=float(w["threshold_pct"]),
                )
                for w in db.watchlist
            ]
            parts = [format_portfolio_markdown(summary, user_id), format_watchlist_markdown(watchlist, user_id)]
        result = {
            "user_id": user_id,
            "intent": "all",
            "summary": summary,
            "watchlist": watchlist,
            "markdown": "\n\n---\n\n".join(parts) or error or "Không có dữ liệu.",
            "error": error,
        }
        box["output"] = {"nav": summary["total_nav"] if summary else None, "watchlist_count": len(watchlist), "error": error}
    note = error or f"đã lập bảng danh mục (NAV {summary['total_nav']:,.0f} VND) + watchlist {len(watchlist)} mã"
    return {"portfolio_watch_result": result, "result": note}


def concept_retrieval_node(state: ChatTeamState, config: RunnableConfig) -> dict:
    """Lấy đoạn giải thích khái niệm từ Qdrant (kèm source_file); answer trả lời bằng đoạn này."""
    from ai_backend.infra.qdrant.answer import NOT_IN_DOCS, answer_concept
    from ai_backend.infra.storage.long_term_memory import get_qdrant_client

    client = get_runtime().context["concept_client"] or get_qdrant_client()
    if client is None:
        found_answer, source_file = NOT_IN_DOCS, None
    else:
        found = answer_concept(state["question"] or "", client=client)
        found_answer, source_file = found.answer, found.source_file
    return {"concept_answer": found_answer, "source_file": source_file, "result": found_answer[:500]}


# ── 3. Memory dài hạn (không phải node: rewrite_question / save_long_term_memory gọi) ──


def recall_memory(user_id: str, query: str) -> list[str]:
    """Đọc long-term memory (Qdrant / in-memory fallback) liên quan câu hỏi; lỗi → rỗng."""
    if not user_id:
        return []
    try:
        return recall_long_term(user_id, query, k=3)
    except Exception:  # noqa: BLE001
        return []


def store_memory(user_id: str, question: str, answer: str) -> None:
    """LLM trích 1 sự thật đáng nhớ dài hạn về người dùng (prompt `memory_fact`) → lưu long-term."""
    if not (user_id and question and answer):
        return
    try:
        prompt = registry().render("memory_fact", question=question, answer=answer)
        fact = call_llm_structured([{"role": "user", "content": prompt}], MemoryFact, params=DETERMINISTIC, max_retries=1)
        if fact.worth_saving and fact.fact.strip():
            save_to_long_term(user_id, fact.fact.strip())
    except Exception as exc:  # noqa: BLE001
        _logger.warning("store_memory lỗi: %s", exc)


# ── 4. Trả lời: answer (final_answer + stream) → save_long_term_memory → END ──


_FINAL_ANSWER_SYSTEM = """Tổng hợp ghi chú từ các worker thành câu trả lời cuối
cho user — ngắn gọn, đầy đủ thông tin đã thu thập được. Không bịa số liệu ngoài ghi chú.
Trả lời bằng tiếng Việt."""

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


def _sanitize(text: str) -> str:
    """Ảnh biểu đồ trong markdown: bỏ tiền tố nhầm 'chart_path:', thêm '/' đầu cho đường dẫn cục bộ."""

    def fix(m: re.Match) -> str:
        url = re.sub(r"^chart_path:\s*", "", m.group(2).strip(), flags=re.IGNORECASE)
        return f"![{m.group(1)}]({url if url.startswith(('/', 'http://', 'https://', 'data:')) else '/' + url})"

    return re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", fix, text or "")


def answer_node(state: ChatTeamState, config: RunnableConfig) -> dict:
    """Trả lời cuối (như final_answer_node demo): task + notes → LLM, stream token; chào/chặn trả thẳng.

    Tạm không qua guardrail_output — answer → save_long_term_memory để SSE nhận đủ token.
    """
    writer = get_stream_writer()
    notes_text = "\n".join(f"[{d}] {n}" for d, n in state["notes"].items())
    messages = [
        {"role": "system", "content": _FINAL_ANSWER_SYSTEM},
        {"role": "user", "content": f"Nhiệm vụ: {state['task']}\n\nGhi chú:\n{notes_text}"},
    ]

    with trace_step(get_runtime().context["trace_span"], "answer", input={"task": state["task"][:200], "notes": list(state["notes"])}) as box:
        text = ""
        
        for token in trace_stream("answer_stream", state["task"], chat_stream(messages, DETERMINISTIC)):
            text += token
            writer(token)
        text = _sanitize(text.strip())
        
        box["output"] = text[:500]

    return {"answer": text, "answer_kind": "final_answer"}


def save_long_term_memory_node(state: ChatTeamState, config: RunnableConfig) -> dict:
    """Cuối lượt: ghi hội thoại ngắn hạn; câu đã qua rewrite (không bị chặn / chào) → lưu sự thật đáng nhớ dài hạn."""
    uid, question, answer = str(state["user_id"] or "").strip(), state["question"] or "", state["answer"] or ""
    memory_store = get_runtime().context["memory_store"]
    if memory_store:
        memory_store.append_conversation(uid, "user", question)
        memory_store.append_conversation(uid, "assistant", answer)
    if state["rewritten"]:
        store_memory(uid, question, answer)
    return {"messages": [AIMessage(content=answer)]}  # trả lời cuối → AssistantState.messages của graph gốc
