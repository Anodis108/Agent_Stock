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


@pytest.fixture(autouse=True)
def _tat_langfuse(monkeypatch):
    """db_agent không cần LangFuse — tránh SSL_CERT_FILE hỏng khi .env bật monitoring."""
    from app.monitoring import tracing

    monkeypatch.setattr(tracing.settings, "monitoring_enabled", False)


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
    """Sai định dạng mã — normalize raise trước khi chạm sqlite3."""
    with pytest.raises(ValueError):
        await run_db(Agent_Input(symbol="HP"))


@pytest.mark.asyncio
async def test_stage_twice_same_url_idempotent(tmp_path, monkeypatch):
    """run_db 2 lần cùng (symbol, url) → 1 pending, cùng id — không nhân hàng."""
    from app.agent_pr.db_agent import nodes as db_nodes

    monkeypatch.setattr(db_nodes, "_DB_PATH", tmp_path / "idem.sqlite3")
    url = "https://cafef.vn/idem-stage.chn"
    inp = Agent_Input(symbol="HPG", candidate_news=[CandidateNews(title="Tin A", url=url)])

    first = await run_db(inp)
    second = await run_db(inp)
    print()
    print("pending 1:", [pw.id for pw in first.pending_writes])
    print("pending 2:", [pw.id for pw in second.pending_writes])

    assert len(first.pending_writes) == 1
    assert len(second.pending_writes) == 1
    assert first.pending_writes[0].id == second.pending_writes[0].id
    assert first.pending_writes[0].url == second.pending_writes[0].url == url


@pytest.mark.asyncio
async def test_approve_twice_idempotent(tmp_path, monkeypatch):
    """Duyệt 2 lần cùng pending_id → cả hai True, `news` chỉ 1 hàng."""
    from app.agent_pr.db_agent import nodes as db_nodes

    monkeypatch.setattr(db_nodes, "_DB_PATH", tmp_path / "idem.sqlite3")
    url = "https://cafef.vn/idem-approve.chn"
    staged = await run_db(
        Agent_Input(symbol="HPG", candidate_news=[CandidateNews(title="Tin B", url=url)])
    )
    pending_id = staged.pending_writes[0].id

    first = approve_pending_write(pending_id, approve=True)
    second = approve_pending_write(pending_id, approve=True)
    print()
    print("approve 1:", first, "approve 2:", second)

    assert first is True
    assert second is True

    after = await run_db(Agent_Input(symbol="HPG"))
    assert [n.url for n in after.saved_news].count(url) == 1
    assert after.pending_writes == []


@pytest.mark.asyncio
async def test_reject_twice_idempotent_then_restage(tmp_path, monkeypatch):
    """Từ chối 2 lần → True, không vào `news`. Stage lại cùng url → cùng id."""
    from app.agent_pr.db_agent import nodes as db_nodes

    monkeypatch.setattr(db_nodes, "_DB_PATH", tmp_path / "idem.sqlite3")
    url = "https://cafef.vn/idem-reject.chn"
    staged = await run_db(
        Agent_Input(symbol="HPG", candidate_news=[CandidateNews(title="Tin C", url=url)])
    )
    pending_id = staged.pending_writes[0].id

    assert approve_pending_write(pending_id, approve=False) is True
    assert approve_pending_write(pending_id, approve=False) is True
    assert approve_pending_write(pending_id, approve=True) is False  # không đảo quyết định

    after_reject = await run_db(Agent_Input(symbol="HPG"))
    assert url not in [n.url for n in after_reject.saved_news]

    restaged = await run_db(
        Agent_Input(symbol="HPG", candidate_news=[CandidateNews(title="Tin C lai", url=url)])
    )
    print()
    print("restage id:", restaged.pending_writes[0].id, "cu:", pending_id)
    assert len(restaged.pending_writes) == 1
    assert restaged.pending_writes[0].id == pending_id


@pytest.mark.asyncio
async def test_approve_then_stage_same_url_khong_soan_lai(tmp_path, monkeypatch):
    """Sau duyệt, stage lại cùng url không tạo pending mới."""
    from app.agent_pr.db_agent import nodes as db_nodes

    monkeypatch.setattr(db_nodes, "_DB_PATH", tmp_path / "idem.sqlite3")
    url = "https://cafef.vn/idem-committed.chn"
    staged = await run_db(
        Agent_Input(symbol="HPG", candidate_news=[CandidateNews(title="Tin D", url=url)])
    )
    assert approve_pending_write(staged.pending_writes[0].id, approve=True)

    again = await run_db(
        Agent_Input(symbol="HPG", candidate_news=[CandidateNews(title="Tin D", url=url)])
    )
    print()
    print("pending sau duyet (ky vong 0):", again.pending_writes)
    assert again.pending_writes == []
    assert url in [n.url for n in again.saved_news]
