"""Synthesis — chạy LLM thật. Khớp Sơ đồ 3d: nêu % / cảnh báo lệch / thiếu tin.

    python -m pytest tests/test_synthesis_agent.py -s -q
"""

from __future__ import annotations

import pytest

from app.agent_pr.craw_agent.schemas import Agent_Output as PriceOut
from app.agent_pr.eval_agent.schemas import Agent_Output as EvalOut
from app.agent_pr.eval_agent.schemas import ScoredItem
from app.agent_pr.news_agent.schemas import Agent_Output as NewsOut
from app.agent_pr.news_agent.schemas import NewsItem
from app.agent_pr.synthesis_agent import Agent_Input, run_synthesis


def _price(pct: float | None) -> PriceOut:
    return PriceOut(symbol="HPG", last=22100, pct_change=pct)


def _news(*titles: str) -> NewsOut:
    return NewsOut(symbol="HPG", articles=[NewsItem(title=t) for t in titles])


def _eval(*, n_pos: int = 0, n_neg: int = 0, match: bool | None = None) -> EvalOut:
    items = [ScoredItem(title="x", sentiment="positive")] * n_pos + [
        ScoredItem(title="x", sentiment="negative")
    ] * n_neg
    return EvalOut(
        symbol="HPG",
        items=items,
        positive_count=n_pos,
        negative_count=n_neg,
        price_matches_news=match,
        has_enough_evidence=bool(items),
    )


def test_neu_chieu_va_phan_tram():
    out = run_synthesis(Agent_Input(price=_price(-4.2), news=_news(), eval=_eval()))
    print(out.answer)
    assert "giảm" in out.answer and "4.2" in out.answer
    assert "chưa tìm thấy tin" in out.answer


def test_canh_bao_lech():
    out = run_synthesis(
        Agent_Input(
            price=_price(-4.2),
            news=_news("HPG báo lợi nhuận tăng trưởng"),
            eval=_eval(n_pos=1, match=False),
        )
    )
    assert "KHÔNG khớp" in out.answer


def test_llm_grounded_answer(monkeypatch):
    from app.agent_pr.synthesis_agent import nodes as n
    from app.agent_pr.synthesis_agent.schemas import Citation, StockAnswer

    monkeypatch.setattr(
        n,
        "chat_parsed_with_usage",
        lambda *a, **k: (
            StockAnswer(
                answer="HPG giảm 4.2% (grounded).",
                confidence=0.9,
                citations=[Citation(source="price", quote="pct -4.2")],
            ),
            {"prompt_tokens": 0, "completion_tokens": 0},
        ),
    )
    out = n.compose(
        {
            "price": _price(-4.2),
            "news": _news(),
            "eval": _eval(),
        }
    )["result"]
    assert out.answer == "HPG giảm 4.2% (grounded)."
    assert out.confidence == 0.9
    assert out.citations[0].source == "price"


def test_thieu_pct_noi_chua_du_lich_su():
    from app.agent_pr.synthesis_agent import nodes as n

    out = n.compose({"price": _price(None), "news": _news(), "eval": _eval()})["result"]
    assert "chưa đủ lịch sử" in out.answer


def test_co_lich_su_db():
    out = run_synthesis(
        Agent_Input(price=_price(1.5), news=_news(), eval=_eval(), n_history=5)
    )
    assert "5 phiên" in out.answer
