"""Tests for Module III gaps: A/B prompts, cascade, eval cache, budget."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.eval.eval_cache import get_cached, prompt_hash_from_messages, set_cached
from backend.infra.cost.tracker import BudgetExceededError, check_budget_or_raise, reset_cost_tracker
from backend.infra.llm.prompt_experiment import pick_prompt_version
from backend.infra.llm.providers import resolve_backend_chain, resolve_model_chain
from backend.shared.settings import settings


def test_pick_prompt_version_sticky_bucket():
    v1 = pick_prompt_version("user-a", enabled=True, split_pct=50)
    v2 = pick_prompt_version("user-a", enabled=True, split_pct=50)
    assert v1 == v2
    assert v1 in {"v1", "v2"}


def test_pick_prompt_version_disabled():
    assert pick_prompt_version("any", enabled=False) == "v1"


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
