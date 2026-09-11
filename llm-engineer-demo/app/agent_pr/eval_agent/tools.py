"""Tools EvalAgent — keyword Sơ đồ 3d. Hàm chấm ở nodes.score."""

from __future__ import annotations

from typing import Annotated

from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState

from app.agent_pr.craw_agent.schemas import Agent_Output as PriceOut
from app.agent_pr.eval_agent.nodes import _sentiment, score
from app.agent_pr.eval_agent.schemas import Agent_Output
from app.agent_pr.news_agent.schemas import Agent_Output as NewsOut


@tool
def classify_headline(title: str) -> str:
    """Chấm 1 tiêu đề: negative | positive | neutral (từ khoá cố định)."""
    return _sentiment(title or "")


@tool
def score_price_vs_news(
    price: Annotated[PriceOut | None, InjectedState("price")] = None,
    news: Annotated[NewsOut | None, InjectedState("news")] = None,
    turn: Annotated[str, InjectedState("turn")] = "",
) -> str:
    """Bắt buộc khi chấm: giá + tin đã có sẵn trong state (không cần tham số) → báo cáo eval.

    Giá/tin lấy thẳng từ state (InjectedState) — KHÔNG bắt LLM chép tay lại
    JSON (trước đây `price_json`/`news_json` là tham số LLM phải tự gõ lại
    nguyên văn; JSON tin dài — nhất là sau khi thêm `summary` — hay bị LLM
    chép cụt giữa chừng, lỗi "Unterminated string", tốn vòng lặp retry, có
    lúc chạm recursion_limit. Đọc thẳng state loại bỏ hẳn lỗi này."""
    try:
        report = score({"price": price, "news": news, "turn": turn})["report"]
        return report.model_dump_json()
    except Exception as exc:
        return Agent_Output(
            symbol="",
            detail=f"Lỗi chấm eval: {exc}. Gọi lại score_price_vs_news.",
        ).model_dump_json()


@tool
def list_eval_keywords() -> str:
    """Liệt kê từ khoá tiêu cực/tích cực EvalAgent dùng."""
    return (
        "negative: xả hàng, bán ròng, giảm sàn, cắt lỗ. "
        "positive: tăng trưởng, lợi nhuận, khuyến nghị mua."
    )


TOOLS = [classify_headline, score_price_vs_news, list_eval_keywords]
