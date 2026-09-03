"""Catalog + retrieval từng agent_pr — không gọi OpenAI."""

from __future__ import annotations

from app.agent_pr.craw_agent.tools import TOOLS as CRAW
from app.agent_pr.db_agent.tools import TOOLS as DB
from app.agent_pr.eval_agent.tools import TOOLS as EVAL
from app.agent_pr.news_agent.tools import TOOLS as NEWS
from app.agent_pr.supervisor_agent.tools import TOOLS as HUB
from app.agent_pr.tool_selection import reset_cache, select_tools


def test_moi_agent_co_catalog_rieng():
    names = {
        "craw": {t.name for t in CRAW},
        "news": {t.name for t in NEWS},
        "eval": {t.name for t in EVAL},
        "db": {t.name for t in DB},
        "hub": {t.name for t in HUB},
    }
    assert names["craw"] == {"normalize_ticker", "fetch_latest_close", "describe_price_source"}
    assert names["news"] == {"normalize_ticker", "fetch_cafef_news", "describe_news_source"}
    assert names["eval"] == {"classify_headline", "score_price_vs_news", "list_eval_keywords"}
    assert names["db"] == {"read_symbol_store", "stage_new_rows", "describe_db_hitl"}
    assert names["hub"] == {"need_price", "need_news", "need_db", "need_eval", "need_synth"}


def test_select_tools_chi_trong_catalog():
    picked = select_tools("", CRAW, k=2)
    assert [t.name for t in picked] == [t.name for t in CRAW[:2]]


def test_select_tools_fail_open(monkeypatch):
    reset_cache()

    def boom(*_a, **_k):
        raise RuntimeError("offline")

    monkeypatch.setattr("app.retrieval.embeddings.embed_passages", boom)
    picked = select_tools("lấy giá HPG", CRAW, k=2)
    assert [t.name for t in picked] == [t.name for t in CRAW[:2]]
    assert "need_price" not in {t.name for t in picked}
