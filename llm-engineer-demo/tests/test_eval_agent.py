"""Eval: 3 case từ khoá (offline) + 1 live HPG.

    python -m pytest tests/test_eval_agent.py -s -q
"""

from __future__ import annotations

import sys

import pytest

from app.agent_pr.craw_agent import Agent_Input as CrawlIn
from app.agent_pr.craw_agent import Agent_Output as PriceOut
from app.agent_pr.craw_agent import run_crawl
from app.agent_pr.eval_agent import Agent_Input, run_eval
from app.agent_pr.news_agent import Agent_Input as NewsIn
from app.agent_pr.news_agent import Agent_Output as NewsOut
from app.agent_pr.news_agent import run_news
from app.agent_pr.news_agent.schemas import NewsItem

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def _price(pct: float | None) -> PriceOut:
    return PriceOut(symbol="HPG", last=22100, pct_change=pct)


def _news(*titles: str) -> NewsOut:
    return NewsOut(symbol="HPG", articles=[NewsItem(title=t) for t in titles])


@pytest.mark.asyncio
async def test_gia_giam_tin_xau_khop():
    """Sơ đồ 3d: −4.2% + xả hàng / giảm sàn → khớp."""
    out = await run_eval(Agent_Input(price=_price(-4.2), news=_news("Khối ngoại xả hàng HPG", "HPG giảm sàn")))
    print("offline:", out.detail)
    assert out.negative_count == 2 and out.price_matches_news is True


@pytest.mark.asyncio
async def test_gia_giam_tin_tot_lech():
    out = await run_eval(Agent_Input(price=_price(-4.2), news=_news("HPG báo lợi nhuận tăng trưởng mạnh")))
    assert out.price_matches_news is False


@pytest.mark.asyncio
async def test_thieu_pct_chua_ro():
    out = await run_eval(Agent_Input(price=_price(None), news=_news("Khối ngoại xả hàng HPG")))
    assert out.price_matches_news is None


@pytest.mark.asyncio
async def test_hpg_online():
    """CafeF thật: nhiều tin neutral vì từ khoá hẹp — in để đối chiếu."""
    price = await run_crawl(CrawlIn(symbol="HPG"))
    news = await run_news(NewsIn(symbol="HPG"))
    out = await run_eval(Agent_Input(price=price, news=news))
    print()
    print(out.symbol, "pct", price.pct_change, "|", out.detail)
    for i, item in enumerate(out.items, 1):
        print(f"  [{i}] {item.sentiment:8}  {item.title}")
    assert out.symbol == "HPG" and out.has_enough_evidence
