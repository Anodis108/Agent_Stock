"""Nodes eval_agent — không gọi mạng.

Một node `score`: khớp từ khoá title → đếm → đối chiếu pct_change.
Cùng ý Sơ đồ 3d / vn-stock-swarm eval_agent.py. Không LLM.

Từ khoá cố ý hẹp: tin CafeF thật hay ra neutral = "chưa rõ", không phải lỗi.
"""

from __future__ import annotations

from app.agent_pr.eval_agent.schemas import Agent_Output, ScoredItem
from app.agent_pr.eval_agent.state import EvalState

# Đúng list Sơ đồ 3d — không thêm "lãi"/"lỗ" (tránh lệch map).
_NEGATIVE = ("xả hàng", "bán ròng", "giảm sàn", "cắt lỗ")
_POSITIVE = ("tăng trưởng", "lợi nhuận", "khuyến nghị mua")


def _sentiment(title: str) -> str:
    """Khớp cả 2 nhóm hoặc không khớp gì → neutral (không đoán liều)."""
    t = title.lower()
    neg = any(k in t for k in _NEGATIVE)
    pos = any(k in t for k in _POSITIVE)
    if neg and not pos:
        return "negative"
    if pos and not neg:
        return "positive"
    return "neutral"


def score(state: EvalState) -> dict:
    """price + news → report. Thiếu một phía / lệch mã → ValueError.

    price_matches_news:
      True  = cùng chiều (giá↓ + tin xấu, hoặc giá không↓ + tin tốt)
      False = lệch
      None  = chưa rõ (thiếu % hoặc không có tin thiên hướng)
    """
    price, news = state.get("price"), state.get("news")
    if price is None or news is None:
        raise ValueError("Eval cần cả price và news")
    if price.symbol != news.symbol:
        raise ValueError(f"Lệch mã giá={price.symbol} tin={news.symbol}")

    items = [ScoredItem(title=a.title, url=a.url, sentiment=_sentiment(a.title)) for a in news.articles]
    n_neg = sum(i.sentiment == "negative" for i in items)
    n_pos = sum(i.sentiment == "positive" for i in items)
    n_neu = sum(i.sentiment == "neutral" for i in items)
    pct = price.pct_change

    # Không có tin rõ chiều → không đối chiếu (tránh nhầm False = lệch).
    if pct is None or (n_neg == 0 and n_pos == 0):
        matched = None
    elif (pct < 0 and n_neg > n_pos) or (pct >= 0 and n_pos > n_neg):
        matched = True
    elif n_neg != n_pos:
        matched = False
    else:
        matched = None

    nhan = {True: "có", False: "không", None: "chưa rõ"}[matched]
    return {
        "report": Agent_Output(
            symbol=price.symbol,
            items=items,
            negative_count=n_neg,
            positive_count=n_pos,
            neutral_count=n_neu,
            has_enough_evidence=bool(items),
            price_matches_news=matched,
            detail=(
                f"{n_neg} tiêu cực · {n_pos} tích cực · {n_neu} trung lập"
                f" — đủ chứng: {'có' if items else 'không'} — khớp giá: {nhan}"
            ),
        )
    }
