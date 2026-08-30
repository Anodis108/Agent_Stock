"""Test live db_agent — đọc/soạn/duyệt qua sqlite3 thật (không mock), in ra
để đối chiếu, giống tinh thần test_craw_agent.py/test_news_agent.py.

Chạy từ llm-engineer-demo:
    python -m pytest tests/test_db_agent.py -s -q

`-s` bắt buộc: không thì pytest nuốt print. Khác craw/news_agent (gọi API
ngoài): db_agent tự chứa (sqlite3 riêng tại data/agent_pr.sqlite3), nên "live"
ở đây nghĩa là chạy thật lên file DB đó, không mock sqlite3.

url dùng timestamp (không hardcode) để mỗi lần pytest chạy là 1 tin MỚI —
tránh bị stage_writes coi là trùng với lần chạy test trước đó (DB là file bền,
không tự xoá giữa các lần chạy).
"""

from __future__ import annotations

import time

import pytest

from app.agent_pr.db_agent import Agent_Input, CandidateNews, approve_pending_write, run_db


@pytest.mark.asyncio
async def test_hpg_read_only():
    """Chỉ ĐỌC (không candidate_news) — chạy hết graph, không cần duyệt gì."""
    out = await run_db(Agent_Input(symbol="HPG"))
    print()
    print("symbol         :", out.symbol)
    print("n_price_history:", len(out.price_history))
    print("n_saved_news   :", len(out.saved_news))
    print("n_pending      :", len(out.pending_writes))
    print("detail         :", out.detail)

    assert out.symbol == "HPG"
    assert out.pending_writes == []


@pytest.mark.asyncio
async def test_stage_then_approve():
    """1 tin mới → soạn pending (chưa vào saved_news) → duyệt → mới thấy trong saved_news."""
    url = f"https://cafef.vn/test-{time.time()}.chn"

    staged = await run_db(
        Agent_Input(symbol="HPG", candidate_news=[CandidateNews(title="Tin test HITL", url=url)])
    )
    print()
    print("sau soan   :", [pw.url for pw in staged.pending_writes])
    assert len(staged.pending_writes) == 1
    assert url not in [n.url for n in staged.saved_news]

    approved = approve_pending_write(staged.pending_writes[0].id, approve=True)
    print("approve ok :", approved)
    assert approved

    after = await run_db(Agent_Input(symbol="HPG"))
    print("sau duyet  :", [n.url for n in after.saved_news])
    assert url in [n.url for n in after.saved_news]


@pytest.mark.asyncio
async def test_stage_duplicate_url_bo_qua():
    """2 candidate cùng url trong 1 lần gọi → chỉ soạn 1 pending, không trùng."""
    url = f"https://cafef.vn/test-dup-{time.time()}.chn"

    out = await run_db(
        Agent_Input(
            symbol="HPG",
            candidate_news=[
                CandidateNews(title="Tin A", url=url),
                CandidateNews(title="Tin A lap lai", url=url),
            ],
        )
    )
    print()
    print("n_pending (ky vong 1):", len(out.pending_writes))
    assert len(out.pending_writes) == 1


@pytest.mark.asyncio
async def test_ma_sai():
    """ABC không whitelist — normalize raise trước khi chạm sqlite3."""
    with pytest.raises(ValueError):
        await run_db(Agent_Input(symbol="ABC"))
