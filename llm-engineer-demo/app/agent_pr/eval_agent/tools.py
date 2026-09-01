"""Tools EvalAgent — keyword Sơ đồ 3d. Hàm chấm ở nodes.score."""

from __future__ import annotations

import json
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
    price_json: str, news_json: str, turn: Annotated[str, InjectedState("turn")] = ""
) -> str:
    """Bắt buộc khi chấm: JSON giá + tin (Agent_Output craw/news) → báo cáo eval. Không sửa số, không bịa sentiment."""
    try:
        price = PriceOut.model_validate_json(price_json) if (price_json or "").strip() not in ("", "{}") else None
        news = None
        if (news_json or "").strip() not in ("", "{}"):
            news = NewsOut.model_validate(json.loads(news_json))
        report = score({"price": price, "news": news, "turn": turn})["report"]
        return report.model_dump_json()
    except Exception as exc:
        return Agent_Output(
            symbol="",
            detail=f"Lỗi chấm eval: {exc}. Kiểm tra JSON giá/tin rồi gọi lại.",
        ).model_dump_json()


@tool
def list_eval_keywords() -> str:
    """Liệt kê từ khoá tiêu cực/tích cực EvalAgent dùng."""
    return (
        "negative: xả hàng, bán ròng, giảm sàn, cắt lỗ. "
        "positive: tăng trưởng, lợi nhuận, khuyến nghị mua."
    )


TOOLS = [classify_headline, score_price_vs_news, list_eval_keywords]
