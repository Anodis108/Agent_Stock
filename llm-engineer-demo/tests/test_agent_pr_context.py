"""Context engineering agent_pr — song song test_agent_m2_memory (phần context).

Không gọi OpenAI: mock completion.chat. History hub là dict {role, content}.
"""

from __future__ import annotations

from app.agent_pr import context
from app.agent_pr.supervisor_agent import nodes
from app.agent_pr.supervisor_agent.state import _append_trim


def test_sliding_window_keeps_recent_and_system():
    msgs = [{"role": "system", "content": "sys"}] + [
        {"role": "user", "content": f"m{i}"} for i in range(30)
    ]
    out = context.sliding_window(msgs, max_messages=5)
    assert len(out) == 6
    assert out[0]["content"] == "sys"
    assert out[-1]["content"] == "m29"


def test_sliding_window_noop_when_short():
    msgs = [{"role": "user", "content": "a"}, {"role": "user", "content": "b"}]
    assert context.sliding_window(msgs, max_messages=20) == msgs


def test_sliding_window_no_duplicate_system_when_in_recent():
    msgs = [{"role": "system", "content": "sys"}, {"role": "user", "content": "u"}]
    out = context.sliding_window(msgs, max_messages=5)
    assert out.count({"role": "system", "content": "sys"}) == 1


def test_estimate_tokens_and_usage():
    msgs = [{"role": "user", "content": "x" * 400}]
    assert context.estimate_tokens(msgs) == 100
    assert context.context_usage(msgs, window_tokens=1000) == 0.1


def test_should_compact_triggers_above_threshold():
    msgs = [{"role": "user", "content": "x" * 4000}]
    assert context.should_compact(msgs, window_tokens=2000, threshold=0.40) is True
    assert context.should_compact(msgs, window_tokens=10000, threshold=0.40) is False


def test_summarize_old_messages_replaces_old_keeps_recent(monkeypatch):
    monkeypatch.setattr(context.completion, "chat", lambda messages, params: "TÓM TẮT")
    msgs = [{"role": "user", "content": f"m{i}"} for i in range(20)]
    out = context.summarize_old_messages(msgs, keep_recent=6)
    assert out[0]["role"] == "system"
    assert "TÓM TẮT" in out[0]["content"]
    assert len(out) == 7
    assert out[-1]["content"] == "m19"


def test_summarize_noop_when_short(monkeypatch):
    called = {"n": 0}
    monkeypatch.setattr(context.completion, "chat", lambda *a, **k: called.update(n=1))
    msgs = [{"role": "user", "content": "a"}]
    assert context.summarize_old_messages(msgs, keep_recent=6) == msgs
    assert called["n"] == 0


def test_reinject_appends_instruction_at_end():
    msgs = [{"role": "system", "content": "sys"}, {"role": "user", "content": "u"}]
    out = context.reinject_instructions(msgs, "QUY TẮC")
    assert out[-1]["role"] == "system"
    assert "QUY TẮC" in out[-1]["content"]
    assert len(out) == 3


def test_append_trim_ghi_de_khi_set_history():
    left = [{"role": "user", "content": "cũ"}]
    right = context.set_history(
        [{"role": "system", "content": "[Tóm tắt hội thoại trước]: x"}]
    )
    out = _append_trim(left, right)
    assert len(out) == 1
    assert "Tóm tắt" in out[0]["content"]


def test_append_trim_van_noi_list_thuong():
    left = [{"i": i} for i in range(18)]
    right = [{"i": 18}, {"i": 19}, {"i": 20}]
    out = _append_trim(left, right)
    assert len(out) == 20
    assert out[0]["i"] == 1
    assert out[-1]["i"] == 20


def test_compact_history_skip_khi_ngan():
    out = nodes.compact_history({"history": [{"role": "user", "content": "giá HPG"}]})
    assert out == {}


def test_compact_history_persist_set_history(monkeypatch):
    monkeypatch.setattr(nodes.context, "should_compact", lambda *a, **k: True)
    monkeypatch.setattr(
        nodes.context,
        "summarize_old_messages",
        lambda hist, keep: [{"role": "system", "content": "SUM"}] + hist[-keep:],
    )
    hist = [{"role": "user", "content": f"m{i}"} for i in range(12)]
    out = nodes.compact_history({"history": hist})
    assert isinstance(out["history"], context.ReplaceHistory)
    assert out["history"][0]["content"] == "SUM"
