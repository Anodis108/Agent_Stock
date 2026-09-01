"""Tools SynthesisAgent — ghép câu. compose() ở nodes.py."""

from __future__ import annotations

from typing import Annotated

from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState

from app.agent_pr.craw_agent.schemas import Agent_Output as PriceOut
from app.agent_pr.eval_agent.schemas import Agent_Output as EvalOut
from app.agent_pr.news_agent.schemas import Agent_Output as NewsOut
from app.agent_pr.synthesis_agent.nodes import compose


@tool
def compose_user_answer(
    price_json: str = "",
    news_json: str = "",
    eval_json: str = "",
    n_history: int = 0,
    question: str = "",
    turn: Annotated[str, InjectedState("turn")] = "",
) -> str:
    """Bắt buộc khi ghép câu: trả lời `question` từ JSON giá + tin + eval. Không crawl, không bịa."""
    try:
        def _load(cls, raw: str):
            text = (raw or "").strip()
            if not text or text == "{}":
                return None
            return cls.model_validate_json(text)

        st = {
            "price": _load(PriceOut, price_json),
            "news": _load(NewsOut, news_json),
            "eval": _load(EvalOut, eval_json),
            "n_history": int(n_history or 0),
            "question": question or "",
            "turn": turn,
        }
        return compose(st)["result"].answer
    except Exception as exc:
        return f"Lỗi ghép câu: {exc}. Thử lại với JSON đủ giá/tin/eval."


@tool
def format_pct_phrase(pct_change: float) -> str:
    """Một cụm 'tăng/giảm x%' từ số pct_change."""
    chieu = "giảm" if pct_change < 0 else "tăng"
    return f"giá {chieu} {abs(pct_change):.1f}% so với phiên liền trước."


@tool
def describe_synth_job() -> str:
    """Synthesis làm gì / không làm gì."""
    return "Chỉ ghép báo cáo đã có. Không bịa tin, không gọi vnstock/CafeF."


TOOLS = [compose_user_answer, format_pct_phrase, describe_synth_job]
