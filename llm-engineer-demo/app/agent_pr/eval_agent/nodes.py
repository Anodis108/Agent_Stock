"""Nodes eval_agent — keyword offline; online chat_parsed(HeadlineBatch).

Một node `score`: chấm title → đếm → đối chiếu pct_change.
Cùng ý Sơ đồ 3d. Từ khoá hẹp = fallback; LLM structured khi có key.
"""

from __future__ import annotations

from app.agent_pr.eval_agent.schemas import Agent_Output, HeadlineBatch, ScoredItem
from app.agent_pr.eval_agent.state import EvalState
from app.agent_pr.react import use_offline_tools
from app.guardrails.injection import bound_messages
from app.llm.completion import chat_parsed
from app.llm.params import DETERMINISTIC
from app.monitoring.tracing import step_parent, trace_step

# Đúng list Sơ đồ 3d — không thêm "lãi"/"lỗ" (tránh lệch map).
_NEGATIVE = ("xả hàng", "bán ròng", "giảm sàn", "cắt lỗ")
_POSITIVE = ("tăng trưởng", "lợi nhuận", "khuyến nghị mua")


_SENTIMENT_SYSTEM = """Phân loại từng tiêu đề tin cổ phiếu VN (giống ProductReview Bài 1).
Few-shot:
- "Khối ngoại xả hàng HPG" → negative
- "HPG báo lợi nhuận tăng trưởng mạnh" → positive
- "HPG họp ĐHĐCĐ thường niên" → neutral
Chỉ negative | positive | neutral. Không bịa tiêu đề. Đúng số lượng / thứ tự đã gửi."""


def _llm_items(articles: list) -> list[ScoredItem] | None:
    """Một lần chat_parsed cho cả lô — type-safe, không regex."""
    if not articles:
        return []
    numbered = "\n".join(f"{i + 1}. {a.title}" for i, a in enumerate(articles))
    batch = chat_parsed(
        bound_messages(_SENTIMENT_SYSTEM, numbered),
        HeadlineBatch,
        DETERMINISTIC,
    )
    if len(batch.items) != len(articles):
        return None
    out: list[ScoredItem] = []
    for art, item in zip(articles, batch.items):
        out.append(
            ScoredItem(
                title=art.title,
                url=getattr(art, "url", "") or "",
                sentiment=item.sentiment,
            )
        )
    return out


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
    """price + news → report. Thiếu / lệch mã → report.detail lỗi, không raise.

    price_matches_news:
      True  = cùng chiều (giá↓ + tin xấu, hoặc giá không↓ + tin tốt)
      False = lệch
      None  = chưa rõ (thiếu % hoặc không có tin thiên hướng)
    """
    price, news = state.get("price"), state.get("news")
    with trace_step(step_parent(state, "eval_agent"), "eval_score", input=getattr(price, "symbol", "")) as t:
        if price is None or news is None:
            report = Agent_Output(
                symbol=str(getattr(price, "symbol", None) or getattr(news, "symbol", None) or ""),
                detail="Lỗi: Eval cần cả price và news. Gọi lại khi đủ dữ liệu.",
            )
            t["output"] = report.detail
            return {"report": report}
        if price.symbol != news.symbol:
            report = Agent_Output(
                symbol=price.symbol,
                detail=(
                    f"Lỗi: lệch mã giá={price.symbol} tin={news.symbol}. "
                    "Chấm lại khi hai phía cùng mã."
                ),
            )
            t["output"] = report.detail
            return {"report": report}

        items = [ScoredItem(title=a.title, url=a.url, sentiment=_sentiment(a.title)) for a in news.articles]
        if items and not use_offline_tools():
            try:
                llm_items = _llm_items(news.articles)
                if llm_items:
                    items = llm_items
            except Exception:
                pass
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
        report = Agent_Output(
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
        t["output"] = report.detail
        return {"report": report}
