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
    symbol = (
        (price.symbol if price else "")
        or (news.symbol if news else "")
        or (ev.symbol if ev else "")
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
                    parts.append(f"tìm thấy {len(news.articles)} tin liên quan.")
            else:
                parts.append("chưa tìm thấy tin liên quan.")

        n = state.get("n_history") or 0
        if n >= 2:
            parts.append(f"lịch sử {n} phiên gần nhất đã có trong DB.")

        if len(parts) == 1:
            parts.append("chưa có báo cáo để ghép.")

        answer = " ".join(parts)
        t["output"] = answer
        return {"result": Agent_Output(answer=answer)}
