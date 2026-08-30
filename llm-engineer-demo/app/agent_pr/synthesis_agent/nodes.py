"""Nodes synthesis — không IO, không chấm lại.

Ghép: chiều giá → số tin + đếm sentiment (eval đã chốt) → cảnh báo lệch
→ (nếu có) lịch sử DB. Thiếu tin không crash, không bịa bài.
"""

from __future__ import annotations

from app.agent_pr.synthesis_agent.schemas import Agent_Output
from app.agent_pr.synthesis_agent.state import SynthState


def compose(state: SynthState) -> dict:
    """price + news + eval → 1 câu. Field `result` là output graph."""
    price, news, ev = state["price"], state["news"], state["eval"]
    parts = [f"{price.symbol}:"]

    if price.pct_change is not None:
        chieu = "giảm" if price.pct_change < 0 else "tăng"
        parts.append(f"giá {chieu} {abs(price.pct_change):.1f}% so với phiên liền trước.")
    else:
        parts.append("chưa đủ lịch sử giá để tính % biến động.")

    if news.articles:
        parts.append(
            f"tìm thấy {len(news.articles)} tin liên quan "
            f"({ev.negative_count} tin tiêu cực, {ev.positive_count} tin tích cực, "
            f"{ev.neutral_count} tin trung lập)."
        )
        # Dùng đúng cờ eval — không tự tính lại khớp giá.
        if ev.price_matches_news is True:
            parts.append("chiều giá khớp với thiên hướng tin tức.")
        elif ev.price_matches_news is False:
            parts.append(
                "lưu ý: chiều giá KHÔNG khớp với thiên hướng tin tức — cần thêm bằng chứng."
            )
    else:
        parts.append("chưa tìm thấy tin liên quan.")

    n = state.get("n_history") or 0
    if n >= 2:
        parts.append(f"lịch sử {n} phiên gần nhất đã có trong DB.")

    return {"result": Agent_Output(answer=" ".join(parts))}
