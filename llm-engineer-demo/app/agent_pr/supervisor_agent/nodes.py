"""Nodes supervisor — điều phối, không lấy giá/tin/chấm trực tiếp.

Đợt 1: craw + news song song. Đợt 2a: eval. Đợt 2b: synthesis (ghép câu).
Chưa db_agent / HITL.
"""

from __future__ import annotations

import asyncio

from app.agent_pr.craw_agent import ALLOWED
from app.agent_pr.craw_agent import Agent_Input as CrawlIn
from app.agent_pr.craw_agent import run_crawl
from app.agent_pr.eval_agent import Agent_Input as EvalIn
from app.agent_pr.eval_agent import run_eval
from app.agent_pr.news_agent import Agent_Input as NewsIn
from app.agent_pr.news_agent import run_news
from app.agent_pr.supervisor_agent.schemas import Agent_Output
from app.agent_pr.supervisor_agent.state import SupervisorState
from app.agent_pr.synthesis_agent import Agent_Input as SynthIn
from app.agent_pr.synthesis_agent import run_synthesis


def normalize(state: SupervisorState) -> dict:
    """Upper mã; whitelist chung craw/news — fail sớm, không tốn 2 HTTP."""
    symbol = str(state.get("symbol") or "").strip().upper()
    if symbol not in ALLOWED:
        raise ValueError(f"Mã '{symbol}' chưa hỗ trợ")
    return {"symbol": symbol}


async def gather(state: SupervisorState) -> dict:
    """Đợt 1 — PriceAgent-lát + NewsAgent chạy cùng lúc, báo cáo về hub."""
    symbol = state["symbol"]
    price, news = await asyncio.gather(
        run_crawl(CrawlIn(symbol=symbol)),
        run_news(NewsIn(symbol=symbol)),
    )
    return {"price": price, "news": news}


async def evaluate(state: SupervisorState) -> dict:
    """Đợt 2 — Eval chỉ sau khi có đủ giá + tin (không tự crawl)."""
    report = await run_eval(EvalIn(price=state["price"], news=state["news"]))
    return {"eval": report}


async def assemble(state: SupervisorState) -> dict:
    """Đợt 2b — gọi synthesis, không tự viết câu ở hub."""
    price, news, ev = state["price"], state["news"], state["eval"]
    syn = await run_synthesis(SynthIn(price=price, news=news, eval=ev))
    return {
        "result": Agent_Output(
            symbol=price.symbol,
            answer=syn.answer,
            price=price,
            news=news,
            eval=ev,
            trace=[
                f"đợt 1: giá {price.source} + {len(news.articles)} tin {news.source}",
                f"đợt 2a: {ev.detail}",
                "đợt 2b: synthesis",
            ],
        )
    }
