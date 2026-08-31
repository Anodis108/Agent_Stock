"""Tools SynthesisAgent — ghép câu. compose() ở nodes.py."""

from __future__ import annotations

from langchain_core.tools import tool

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
) -> str:
    """Ghép câu trả lời tiếng Việt từ JSON giá + tin + eval (không crawl, không chấm lại)."""

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
    }
    return compose(st)["result"].answer


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
