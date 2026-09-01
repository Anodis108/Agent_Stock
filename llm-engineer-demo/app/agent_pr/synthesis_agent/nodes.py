"""Nodes synthesis — ghép câu từ báo cáo. Không crawl, không chấm lại.

Offline / lỗi LLM: template join (test ổn định).
Online: chat_parsed(StockAnswer) — Bài 1 schema + Bài 5 grounding (chỉ dùng báo cáo).
"""

from __future__ import annotations

from app.agent_pr.react import use_offline_tools
from app.agent_pr.synthesis_agent.schemas import Agent_Output, Citation, StockAnswer
from app.agent_pr.synthesis_agent.state import SynthState
from app.guardrails.injection import bound_messages
from app.llm.completion import chat_parsed
from app.llm.params import DETERMINISTIC
from app.monitoring.tracing import trace_step

_GROUNDING = """Bạn là SynthesisAgent hỏi–đáp cổ phiếu VN.

Quy tắc (RAG generation — chỉ bám báo cáo):
- CHỈ dùng số liệu, tiêu đề, đếm sentiment trong BÁO CÁO bên dưới.
- Không bịa giá, tin, mã. Thiếu dữ liệu thì nói thiếu.
- Tiếng Việt, ngắn. Trích citations.source = price|news|eval|db."""


def _compose_template(state: SynthState) -> tuple[str, str, list[Citation]]:
    """Ghép deterministic — fallback khi offline hoặc parse lỗi."""
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
    """Template luôn có; LLM structured khi online — lỗi thì giữ template."""
    symbol, template, cites = _compose_template(state)
    with trace_step(state.get("_trace_span"), "synth_compose", input=symbol) as t:
        result = Agent_Output(
            answer=template,
            confidence=0.7 if cites else 0.3,
            citations=cites,
        )
        if not use_offline_tools():
            price, news, ev = state.get("price"), state.get("news"), state.get("eval")
            db = state.get("db")
            reports = (
                f"price={price.model_dump() if price else None}\n"
                f"news={news.model_dump() if news else None}\n"
                f"eval={ev.model_dump() if ev else None}\n"
                f"db_detail={getattr(db, 'detail', None)}\n"
                f"n_history={state.get('n_history') or 0}"
            )
            try:
                parsed = chat_parsed(
                    bound_messages(_GROUNDING, f"BÁO CÁO:\n{reports}\n\nGhép câu trả lời."),
                    StockAnswer,
                    DETERMINISTIC,
                )
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
