"""Nodes synthesis — ghép câu từ báo cáo. Không crawl, không chấm lại.

Lỗi LLM: template join (giữ answer luôn có, không raise).
chat_parsed(StockAnswer) — Bài 1 schema + Bài 5 grounding (chỉ dùng báo cáo).
"""

from __future__ import annotations

from app.agent_pr.synthesis_agent.schemas import Agent_Output, Citation, StockAnswer
from app.agent_pr.synthesis_agent.state import SynthState
from app.config import settings
from app.guardrails.injection import bound_messages
from app.llm.completion import chat_parsed_with_usage
from app.llm.params import DETERMINISTIC
from app.monitoring.tracing import record_usage, step_parent, trace_step

_GROUNDING = """Bạn là SynthesisAgent hỏi–đáp cổ phiếu VN.

Quy tắc (RAG generation — chỉ bám báo cáo):
- Trả lời ĐÚNG câu hỏi user (tăng/giảm so với hôm qua → chiều + %; giá bao nhiêu → số VND).
- CHỈ dùng số liệu, tiêu đề, đếm sentiment trong BÁO CÁO bên dưới.
- Không bịa giá, tin, mã.

BẮT BUỘC nêu rõ (đây là cảnh báo an toàn, không được bỏ qua dù câu hỏi không hỏi trực tiếp):
- Báo cáo đã nói rõ "đủ dữ liệu" hay "CHƯA đủ lịch sử" cho phần giá — PHẢI theo
  đúng kết luận đó, không tự suy diễn thêm.
- eval.price_matches_news=False → PHẢI nêu rõ CẢNH BÁO chiều giá KHÔNG khớp với thiên hướng tin tức (dùng đúng cụm "KHÔNG khớp" hoặc "lệch").
- news báo "chưa tìm thấy tin" → PHẢI nói rõ điều đó, không được im lặng bỏ qua phần tin.
- n_history >= 2 (đã có lịch sử DB) → PHẢI nêu số phiên lịch sử đã có (vd. "5 phiên gần nhất đã có trong DB").

Tiếng Việt, ngắn gọn nhưng không được lược bỏ các cảnh báo bắt buộc trên. Trích citations.source = price|news|eval|db."""


def _compose_template(state: SynthState) -> tuple[str, str, list[Citation]]:
    """Ghép deterministic — fallback khi LLM lỗi hoặc parse lỗi."""
    price, news, ev = state.get("price"), state.get("news"), state.get("eval")
    db = state.get("db")
    symbol = (
        (price.symbol if price else "")
        or (news.symbol if news else "")
        or (ev.symbol if ev else "")
        or (db.symbol if db else "")
        or "?"
    )
    parts = [f"{symbol}:"]
    cites: list[Citation] = []

    if price:
        if price.pct_change is not None:
            chieu = "giảm" if price.pct_change < 0 else "tăng"
            quote = f"giá {chieu} {abs(price.pct_change):.1f}% so với phiên liền trước."
            parts.append(quote)
            cites.append(Citation(source="price", quote=quote.rstrip(".")))
        else:
            parts.append("chưa đủ lịch sử giá để tính % biến động.")

    if news:
        if news.articles:
            if ev:
                parts.append(
                    f"tìm thấy {len(news.articles)} tin liên quan "
                    f"({ev.negative_count} tin tiêu cực, {ev.positive_count} tin tích cực, "
                    f"{ev.neutral_count} tin trung lập)."
                )
                if ev.price_matches_news is True:
                    parts.append("chiều giá khớp với thiên hướng tin tức.")
                elif ev.price_matches_news is False:
                    parts.append(
                        "lưu ý: chiều giá KHÔNG khớp với thiên hướng tin tức — cần thêm bằng chứng."
                    )
                cites.append(Citation(source="eval", quote=ev.detail or "eval"))
            else:
                parts.append(f"tìm thấy {len(news.articles)} tin {news.source}.")
            titles = [a.title for a in news.articles if getattr(a, "title", None)]
            if titles:
                shown = titles[:8]
                extra = f" (+{len(titles) - 8} tin nữa)" if len(titles) > 8 else ""
                parts.append("Tiêu đề: " + "; ".join(shown) + extra + ".")
                cites.append(Citation(source="news", quote=shown[0]))
        else:
            parts.append("chưa tìm thấy tin liên quan.")

    n = state.get("n_history") or 0
    if n >= 2:
        parts.append(f"lịch sử {n} phiên gần nhất đã có trong DB.")
        cites.append(Citation(source="db", quote=f"{n} phiên"))
    if db and db.pending_writes:
        n_p = len(db.pending_writes)
        parts.append(
            f"Đã soạn {n_p} lệnh ghi bài chưa có trong kho "
            "(chờ duyệt HITL — chưa COMMIT vào bảng news)."
        )
        samples = [pw.title for pw in db.pending_writes[:5] if pw.title]
        if samples:
            parts.append("Bài chờ duyệt: " + "; ".join(samples) + ".")

    if len(parts) == 1:
        parts.append("chưa có báo cáo để ghép.")

    return symbol, " ".join(parts), cites


def compose(state: SynthState) -> dict:
    """Template luôn có; LLM structured ghi đè — lỗi thì giữ template."""
    symbol, template, cites = _compose_template(state)
    with trace_step(step_parent(state, "synth_agent"), "synth_compose", input=symbol) as t:
        result = Agent_Output(
            answer=template,
            confidence=0.7 if cites else 0.3,
            citations=cites,
        )
        price, news, ev = state.get("price"), state.get("news"), state.get("eval")
        db = state.get("db")
        n_history = int(state.get("n_history") or 0)
        # Diễn giải rõ từng field quan trọng thay vì model_dump() thô — dump thô
        # kèm prev_close=None (dù pct_change đã có giá trị) khiến model hiểu
        # nhầm "thiếu phiên trước" = "thiếu lịch sử", bỏ qua pct_change đã tính sẵn.
        if price is None:
            price_line = "price: không có dữ liệu giá."
        elif price.pct_change is None:
            price_line = f"price: giá hiện tại {price.last} VND. CHƯA đủ lịch sử để tính % biến động."
        else:
            price_line = (
                f"price: giá hiện tại {price.last} VND, đã tính được pct_change={price.pct_change}% "
                "(đủ dữ liệu, không phải thiếu lịch sử)."
            )
        news_line = (
            "news: chưa tìm thấy tin liên quan."
            if not news or not news.articles
            else f"news: {len(news.articles)} tin — {news.model_dump()}"
        )
        # price_matches_news diễn giải rõ True/False/None — dump thô dễ khiến
        # model tự suy diễn "None" thành "không khớp" (hallucination).
        if ev is None:
            eval_line = "eval: không có báo cáo chấm điểm."
        elif ev.price_matches_news is True:
            eval_line = f"eval: chiều giá KHỚP với thiên hướng tin tức. Chi tiết: {ev.detail or ev.model_dump()}"
        elif ev.price_matches_news is False:
            eval_line = f"eval: chiều giá KHÔNG khớp với thiên hướng tin tức. Chi tiết: {ev.detail or ev.model_dump()}"
        else:
            eval_line = (
                f"eval: CHƯA đủ bằng chứng để kết luận khớp hay không khớp giữa giá và tin "
                f"(không được tự suy diễn khớp/không khớp). Chi tiết: {ev.detail or ev.model_dump()}"
            )
        db_line = (
            f"n_history: {n_history} — đã có {n_history} phiên lịch sử trong DB, PHẢI nêu con số này."
            if n_history >= 2
            else f"n_history: {n_history} (chưa đủ lịch sử DB để nêu số phiên)"
        ) + f"\ndb_detail: {getattr(db, 'detail', None)}"
        reports = f"{price_line}\n{news_line}\n{eval_line}\n{db_line}"
        q = str(state.get("rewritten_question") or state.get("question") or "").strip()
        try:
            parsed, usage = chat_parsed_with_usage(
                bound_messages(
                    _GROUNDING,
                    f"CÂU HỎI: {q or '(không có)'}\n\nBÁO CÁO:\n{reports}\n\n"
                    "Trả lời câu hỏi, chỉ dùng báo cáo.",
                ),
                StockAnswer,
                DETERMINISTIC,
            )
            record_usage(str(state.get("turn") or ""), settings.llm_model, **usage)
            if (parsed.answer or "").strip():
                result = Agent_Output(
                    answer=parsed.answer.strip(),
                    confidence=parsed.confidence,
                    citations=parsed.citations or cites,
                )
        except Exception:
            pass
        t["output"] = result.answer
        return {"result": result}
