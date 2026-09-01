"""Test live news_agent — gọi CafeF News.ashx, in tin để đối chiếu trang mã.

Chạy từ llm-engineer-demo:
    python -m pytest tests/test_news_agent.py -s -q

`-s` bắt buộc. Không hardcode title: tin đổi theo ngày.
Đúng/sai: so title + url với https://cafef.vn/du-lieu/hose/hpg-cong-ty-co-phan-tap-doan-hoa-phat.chn
"""

from __future__ import annotations

import sys

import pytest

from app.agent_pr.news_agent import Agent_Input, run_news

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def test_hpg_online():
    """HPG — graph chạy hết, mỗi tin có title + url CafeF."""
    out = run_news(Agent_Input(symbol="HPG"))
    print()
    print("symbol :", out.symbol)
    print("source :", out.source)
    print("n_news :", len(out.articles))
    for i, a in enumerate(out.articles, 1):
        print(f"  [{i}] {a.publish_time}  {a.title}")
        print(f"       {a.url}")

    assert out.symbol == "HPG"
    assert out.source == "cafef"
    assert out.articles
    assert out.articles[0].title
    assert out.articles[0].url.startswith("https://cafef.vn/")


def test_ma_sai():
    """Không chặn regex — chỉ upper/strip."""
    from app.agent_pr.news_agent.nodes import normalize

    assert normalize({"symbol": "hp"})["symbol"] == "HP"
