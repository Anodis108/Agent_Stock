"""Nodes synthesis — không IO, không chấm lại.

Ghép: chiều giá → số tin + đếm sentiment (eval đã chốt) → cảnh báo lệch
→ (nếu có) lịch sử DB. Thiếu tin không crash, không bịa bài.
"""

from __future__ import annotations

from app.agent_pr.synthesis_agent.schemas import Agent_Output
from app.agent_pr.synthesis_agent.state import SynthState
from app.monitoring.tracing import trace_step


def compose(state: SynthState) -> dict:
    """Ghép báo cáo hub đã thu — thiếu worker thì bỏ đoạn đó, không bịa."""
    price, news, ev = state.get("price"), state.get("news"), state.get("eval")
    db = state.get("db")
    symbol = (
        (price.symbol if price else "")
        or (news.symbol if news else "")
        or (ev.symbol if ev else "")
        or (db.symbol if db else "")
        or "?"
    )
    with trace_step(state.get("_trace_span"), "synth_compose", input=symbol) as t:
        parts = [f"{symbol}:"]

        if price:
            if price.pct_change is not None:
                chieu = "giảm" if price.pct_change < 0 else "tăng"
                parts.append(
                    f"giá {chieu} {abs(price.pct_change):.1f}% so với phiên liền trước."
                )
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
                else:
                    parts.append(f"tìm thấy {len(news.articles)} tin {news.source}.")
                titles = [a.title for a in news.articles if getattr(a, "title", None)]
                if titles:
                    shown = titles[:8]
                    extra = f" (+{len(titles) - 8} tin nữa)" if len(titles) > 8 else ""
                    parts.append("Tiêu đề: " + "; ".join(shown) + extra + ".")
            else:
                parts.append("chưa tìm thấy tin liên quan.")

        n = state.get("n_history") or 0
        if n >= 2:
            parts.append(f"lịch sử {n} phiên gần nhất đã có trong DB.")
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

        answer = " ".join(parts)
        t["output"] = answer
        return {"result": Agent_Output(answer=answer)}
