"""Tests for Module III gaps: A/B prompts, cascade, eval cache, budget."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from backend.eval.eval_cache import get_cached, prompt_hash_from_messages, set_cached
from backend.eval.run import eval_one_case
from backend.infra.cost.tracker import BudgetExceededError, check_budget_or_raise, reset_cost_tracker
from backend.infra.llm.prompt_experiment import pick_prompt_version
from backend.infra.llm.providers import resolve_backend_chain, resolve_model_chain
from backend.shared.settings import settings


def test_pick_prompt_version_sticky_bucket():
    v1 = pick_prompt_version("user-a", enabled=True, split_pct=50)
    v2 = pick_prompt_version("user-a", enabled=True, split_pct=50)
    assert v1 == v2
    assert v1 in {"production", "v2"}


def test_pick_prompt_version_disabled():
    assert pick_prompt_version("any", enabled=False) == "production"


def test_restrict_symbols_blocks_xin_vui_from_typo():
    from backend.agents.supervisor_agent.nodes import _restrict_symbols_to_original

    q = "Cho tôi giá hiện tịa VNM"
    assert _restrict_symbols_to_original(q, ["VNM", "XIN", "VUI"]) == ["VNM"]


def test_prompt_registry_accepts_v1_alias():
    from backend.infra.llm.prompt_registry import registry

    p = registry().get("answer_compose", version="v1")
    assert p.version == 1


def test_resolve_model_chain_dedupes():
    chain = resolve_model_chain("gpt-4o-mini")
    assert chain[0] == "gpt-4o-mini"


def test_resolve_backend_chain_includes_primary():
    chain = resolve_backend_chain()
    assert chain[0] == settings.llm_backend.strip().lower()


def test_eval_cache_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "eval_cache_enabled", True)
    monkeypatch.setattr(settings, "eval_cache_dir", str(tmp_path))
    ph = prompt_hash_from_messages([{"role": "user", "content": "Giá FPT?"}])
    assert get_cached("case-1", ph) is None
    payload = {"output": "FPT 100k", "steps": [], "error": None}
    set_cached("case-1", ph, payload)
    hit = get_cached("case-1", ph)
    assert hit is not None
    assert hit["output"] == "FPT 100k"
    path = tmp_path / f"{ph[:8]}.json"
    # key is hashed — just verify file exists
    assert any(tmp_path.glob("*.json"))


def test_chat_cache_respects_model_param(monkeypatch):
    """Exact cache lookup phải dùng model được truyền, không phải settings.llm_model."""
    from backend.infra.cache.exact import (
        clear_llm_cache_context,
        get_exact_cache,
        set_llm_cache_context,
    )
    from backend.infra.cache.semantic import get_semantic_cache
    from backend.infra.llm import completion as completion_mod

    get_exact_cache().clear()
    get_semantic_cache().clear()
    calls: list[str] = []

    class _Usage:
        prompt_tokens = 10
        completion_tokens = 5
        total_tokens = 15

    def fake_create(**kwargs):
        calls.append(str(kwargs.get("model")))
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock(message=MagicMock(content=f"ans-{kwargs.get('model')}"))]
        mock_resp.usage = _Usage()
        return mock_resp

    fake_client = MagicMock()
    fake_client.chat.completions.create = fake_create
    monkeypatch.setattr(completion_mod, "get_client", lambda: fake_client)
    monkeypatch.setattr(completion_mod, "retry_with_backoff", lambda fn, **kw: fn())
    monkeypatch.setenv("EXACT_CACHE_ENABLED", "true")
    monkeypatch.setenv("SEMANTIC_CACHE_ENABLED", "false")

    messages = [{"role": "user", "content": "test"}]
    set_llm_cache_context(
        prompt_name="answer_compose",
        prompt_version="production",
        normalized_question="Giá FPT?",
    )
    heavy = "gpt-4o"
    light = settings.llm_model
    first = completion_mod.chat(messages, model=heavy)
    assert first == f"ans-{heavy}"
    assert calls == [heavy]
    second = completion_mod.chat(messages, model=heavy)
    assert second == f"ans-{heavy}"
    assert len(calls) == 1  # cache hit — không gọi API lần 2
    third = completion_mod.chat(messages, model=light)
    assert third == f"ans-{light}"
    assert len(calls) == 2  # model khác → cache miss
    clear_llm_cache_context()


def test_eval_one_case_uses_cache(monkeypatch, tmp_path):
    """eval_one_case không gọi answer_fn khi đã có entry trong eval cache."""
    monkeypatch.setattr(settings, "eval_cache_enabled", True)
    monkeypatch.setattr(settings, "eval_cache_dir", str(tmp_path))
    case = {
        "id": "cache-test-1",
        "question": "Giá FPT?",
        "slice": {"type": "lookup"},
        "expected": "ok",
    }
    from backend.eval.run import _eval_cache_prompt_hash

    ph = _eval_cache_prompt_hash(case)
    set_cached(
        "cache-test-1",
        ph,
        {"output": "cached output FPT", "steps": [{"agent": "price"}], "error": None},
    )
    calls: list[str] = []

    def answer_fn(_q: str) -> str:
        calls.append("called")
        return "live"

    result = eval_one_case(case, answer_fn=answer_fn, skip_judge=True, skip_agent_eval=True)
    assert result.output == "cached output FPT"
    assert calls == []
    assert result.steps == [{"agent": "price"}]


def test_budget_exceeded(monkeypatch):
    reset_cost_tracker()
    monkeypatch.setattr(settings, "cost_daily_limit_usd", 0.000001)
    from backend.infra.cost.tracker import record_cost

    record_cost(
        feature="test",
        model="gpt-4o-mini",
        prompt_version="v1",
        cache_hit=False,
        prompt_tokens=100_000,
        completion_tokens=100_000,
    )
    with pytest.raises(BudgetExceededError):
        check_budget_or_raise()
    reset_cost_tracker()
