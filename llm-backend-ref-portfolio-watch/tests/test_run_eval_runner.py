"""Phase 9 — eval runner: answer_question + ghép 2 scorer."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_eval.py"


def _load_run_eval():
    name = "run_eval_runner"
    spec = importlib.util.spec_from_file_location(name, SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_run_eval_merges_rule_and_judge_per_case() -> None:
    mod = _load_run_eval()
    data = mod.load_golden_dataset()
    by_id = {c["id"]: c for c in data["cases"]}
    cases = [by_id["lookup_01"], by_id["out_of_scope_01"], by_id["injection_01"]]

    answers = {
        by_id["lookup_01"]["question"]: "Giá FPT hôm nay 100.",
        by_id["out_of_scope_01"]["question"]: "Ngoài phạm vi theo dõi danh mục.",
        by_id["injection_01"]["question"]: "Tôi bỏ qua yêu cầu đó.",
    }
    calls: list[str] = []

    def answer_fn(q: str) -> str:
        calls.append(q)
        return answers[q]

    def fake_parse(*_a, **_k):
        return mod.LlmJudgeScore(
            correctness=4, completeness=4, grounding=4, reasoning="ok"
        )

    results = mod.run_eval(cases, answer_fn=answer_fn, chat_parsed_fn=fake_parse)
    assert len(results) == 3
    assert calls == [c["question"] for c in cases]

    assert results[0].case_id == "lookup_01"
    assert results[0].rule.passed is True
    assert results[0].judge.skipped is False
    assert results[0].passed is True

    assert results[1].slice_type == "out_of_scope"
    assert results[1].judge.skipped is True
    assert results[1].passed is True

    assert results[2].slice_type == "injection"
    assert results[2].judge.skipped is True
    assert results[2].passed is True


def test_run_eval_lookup_fails_when_judge_fails() -> None:
    mod = _load_run_eval()
    case = {
        "id": "lookup_x",
        "question": "Giá FPT?",
        "expected": "có FPT",
        "slice": {"type": "lookup", "multihop": False},
        "must_include": ["FPT"],
        "must_not_include": [],
    }

    def answer_fn(_q: str) -> str:
        return "FPT giá 1."

    def weak_parse(*_a, **_k):
        return mod.LlmJudgeScore(
            correctness=1, completeness=1, grounding=1, reasoning="yếu"
        )

    results = mod.run_eval([case], answer_fn=answer_fn, chat_parsed_fn=weak_parse)
    assert results[0].rule.passed is True
    assert results[0].judge.passed is False
    assert results[0].passed is False


def test_run_eval_skips_judge_when_rule_fails() -> None:
    mod = _load_run_eval()
    case = {
        "id": "lookup_y",
        "question": "Giá FPT?",
        "expected": "có FPT",
        "slice": {"type": "lookup", "multihop": False},
        "must_include": ["FPT"],
        "must_not_include": [],
    }

    def answer_fn(_q: str) -> str:
        return "không nhắc mã"

    def boom(*_a, **_k):
        raise AssertionError("judge must not run")

    results = mod.run_eval([case], answer_fn=answer_fn, chat_parsed_fn=boom)
    assert results[0].rule.passed is False
    assert results[0].judge.skipped is True
    assert results[0].passed is False


def test_run_eval_limit_and_answer_fn_error() -> None:
    mod = _load_run_eval()
    data = mod.load_golden_dataset()
    results = mod.run_eval(
        data["cases"],
        answer_fn=lambda _q: "FPT VNM HPG",
        skip_judge=True,
        limit=2,
    )
    assert len(results) == 2

    def boom(_q: str) -> str:
        raise RuntimeError("down")

    one = mod.eval_one_case(
        data["cases"][0], answer_fn=boom, skip_judge=True
    )
    assert one.error and "down" in one.error
    assert one.passed is False


def test_make_answer_fn_calls_answer_question(monkeypatch) -> None:
    mod = _load_run_eval()
    seen: dict = {}

    class FakeResult:
        answer = "Giá FPT từ app"

    def fake_answer_question(question, **kwargs):
        seen["question"] = question
        seen["kwargs"] = kwargs
        return FakeResult()

    class Deps:
        price_source = object()
        news_source = object()
        history_store = object()
        memory_store = object()

    monkeypatch.setattr(
        "src.portfolio_watch.application.answer_question.answer_question",
        fake_answer_question,
    )
    monkeypatch.setattr(
        "src.portfolio_watch.api.deps.get_app_deps",
        lambda: Deps(),
    )
    fn = mod.make_answer_fn()
    assert fn("Giá FPT?") == "Giá FPT từ app"
    assert seen["question"] == "Giá FPT?"


def test_checklist_runner_checked() -> None:
    text = (ROOT / "specs" / "implementation-plan.md").read_text(encoding="utf-8")
    assert (
        "- [x] `scripts/run_eval.py` — runner: gọi `application/answer_question.py`"
        in text
    )
