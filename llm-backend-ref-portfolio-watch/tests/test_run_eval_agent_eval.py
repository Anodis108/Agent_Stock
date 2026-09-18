"""Phase 1 — task_success + trajectory + --case-id."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_eval.py"


def _load():
    name = "run_eval_agent_eval"
    spec = importlib.util.spec_from_file_location(name, SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_filter_case_id_and_unknown():
    mod = _load()
    data = mod.load_golden_dataset()
    one = mod.filter_golden_cases(data["cases"], case_id="lookup_01")
    assert len(one) == 1 and one[0]["id"] == "lookup_01"
    try:
        mod.filter_golden_cases(data["cases"], case_id="no_such_case")
        assert False, "expected ValueError"
    except ValueError as e:
        assert "unknown case-id" in str(e)


def test_task_success_fails_lookup_when_success_false():
    mod = _load()
    case = {
        "id": "lookup_x",
        "question": "Giá FPT?",
        "expected": "có FPT và giá",
        "slice": {"type": "lookup", "multihop": False},
        "must_include": ["FPT"],
        "must_not_include": [],
    }

    def answer_fn(_q: str) -> str:
        return "FPT giá 100."

    def judge_ok(*_a, **_k):
        return mod.LlmJudgeScore(
            correctness=4, completeness=4, grounding=4, reasoning="ok"
        )

    def agent_fail(messages, schema, *_a, **_k):
        from src.portfolio_watch.infra.eval.agent_scorers import (
            TaskSuccessResult,
            TrajectoryResult,
        )

        if getattr(schema, "__name__", "") == "TaskSuccessResult":
            return TaskSuccessResult(
                success=False, score=0.2, reasoning="thiếu số liệu"
            )
        return TrajectoryResult(
            efficiency=4,
            logical_order=4,
            tool_correctness=4,
            recovery=5,
            issues=[],
        )

    results = mod.run_eval(
        [case],
        answer_fn=answer_fn,
        chat_parsed_fn=judge_ok,
        agent_eval_parsed_fn=agent_fail,
        skip_judge=False,
        skip_agent_eval=False,
    )
    assert results[0].rule.passed is True
    assert results[0].task_success is not None
    assert results[0].task_success.skipped is False
    assert results[0].task_success.result.success is False
    assert results[0].passed is False


def test_trajectory_warn_does_not_fail_case():
    mod = _load()
    from src.portfolio_watch.infra.eval.agent_scorers import (
        TaskSuccessResult,
        TrajectoryResult,
    )

    case = {
        "id": "lookup_y",
        "question": "Giá FPT?",
        "expected": "có FPT",
        "slice": {"type": "lookup", "multihop": False},
        "must_include": ["FPT"],
        "must_not_include": [],
    }

    def answer_fn(_q: str) -> str:
        answer_fn.last_steps = [
            {"tool": "supervisor", "args": {}, "observation": "messed up order"},
            {"tool": "eval_agent", "args": {}, "observation": "too early"},
        ]
        return "FPT giá 100."

    answer_fn.last_steps = []

    def judge_ok(*_a, **_k):
        return mod.LlmJudgeScore(
            correctness=5, completeness=5, grounding=5, reasoning="ok"
        )

    def agent_parse(messages, schema, *_a, **_k):
        if schema is TaskSuccessResult:
            return TaskSuccessResult(success=True, score=0.9, reasoning="ok")
        return TrajectoryResult(
            efficiency=1,
            logical_order=1,
            tool_correctness=1,
            recovery=5,
            issues=["sai thứ tự"],
        )

    results = mod.run_eval(
        [case],
        answer_fn=answer_fn,
        chat_parsed_fn=judge_ok,
        agent_eval_parsed_fn=agent_parse,
    )
    assert results[0].passed is True
    assert results[0].trajectory is not None
    assert results[0].trajectory.warn is True
    text = mod.format_trajectory_warnings(results)
    assert "lookup_y" in text


def test_steps_from_answer_result():
    from src.portfolio_watch.infra.eval.agent_scorers import steps_from_answer_result
    from types import SimpleNamespace

    result = SimpleNamespace(
        rewritten=SimpleNamespace(rewritten="giá FPT", symbol="FPT"),
        routing=SimpleNamespace(
            agents_to_call=["price"], reason="lookup", route="price_lookup"
        ),
        price=SimpleNamespace(
            symbol="FPT", latest_close=100.0, change_pct=1.0, error=None
        ),
        news=None,
        eval_result=None,
        answer="FPT giá 100",
    )
    steps = steps_from_answer_result(result)
    names = [s["tool"] for s in steps]
    assert names == ["rewrite_question", "supervisor", "price_agent", "answer_composer"]


def test_cli_case_id_help_and_filter_in_main():
    mod = _load()
    # unknown case-id exits via ValueError before LLM — catch in run_eval
    try:
        mod.run_eval(case_id="nope", skip_judge=True, skip_agent_eval=True)
        assert False
    except ValueError:
        pass
