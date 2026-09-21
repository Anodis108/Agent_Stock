"""Agents — vnstock/Cafef thật + guardrail."""

from __future__ import annotations

import pytest

from src.portfolio_watch.agents import answer_composer, synthesis_agent
from src.portfolio_watch.domain.agents.event_classifier import classify_event
from src.portfolio_watch.domain.agents.news_agent import run_news_agent
from src.portfolio_watch.domain.agents.price_agent import run_price_agent
from src.portfolio_watch.domain.entities import EventRoute
from src.portfolio_watch.domain.guardrails.output_checks import check_output
from src.portfolio_watch.infra.market_data import CafefNewsSource, VnstockPriceSource


def test_price_agent_real_vnstock():
    r = run_price_agent("FPT", VnstockPriceSource())
    if r.error:
        pytest.skip(f"vnstock không khả dụng: {r.error}")
    assert r.latest_close is not None
    assert r.change_pct is not None


def test_guardrail_blocks_buy_sell_advice():
    buy = check_output("Alert", "Nhà đầu tư nên mua FPT.", evidence=["change_pct=-4%"])
    sell = check_output("Alert", "Nhà đầu tư nên bán FPT.", evidence=["change_pct=-4%"])
    assert buy.ok is False and sell.ok is False


def test_guardrail_shared_by_synthesis_and_answer():
    assert synthesis_agent.nodes.check_output is check_output
    assert answer_composer.nodes.check_output is check_output


def test_event_classifier_with_real_price_and_news():
    """LLM classifier + giá/tin thật — không assert route cố định."""
    price = run_price_agent("FPT", VnstockPriceSource())
    if price.error:
        pytest.skip(f"vnstock không khả dụng: {price.error}")
    news = run_news_agent("FPT", CafefNewsSource(), days=7)
    routing = classify_event(price, news, threshold_pct=3.0)
    assert routing.route in (EventRoute.NORMAL, EventRoute.ABNORMAL)
    assert routing.reason.strip()
    assert not routing.reason.startswith("classifier lỗi")
