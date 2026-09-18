"""Phase 9 — rule-based scorer in scripts/run_eval.py."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_eval.py"


def _load_run_eval():
    spec = importlib.util.spec_from_file_location("run_eval", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["run_eval"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_score_rule_based_must_include_and_must_not() -> None:
    mod = _load_run_eval()
    ok = mod.score_rule_based(
        "Giá FPT hôm nay 100",
        must_include=["FPT"],
        must_not_include=["nên mua", "nên bán"],
    )
    assert ok.passed is True
    assert ok.missing == []
    assert ok.forbidden_found == []

    miss = mod.score_rule_based(
        "Thị trường xanh",
        must_include=["FPT"],
        must_not_include=[],
    )
    assert miss.passed is False
    assert miss.missing == ["FPT"]

    bad = mod.score_rule_based(
        "FPT nên mua ngay",
        must_include=["FPT"],
        must_not_include=["nên mua"],
    )
    assert bad.passed is False
    assert "nên mua" in bad.forbidden_found


def test_score_rule_based_case_insensitive() -> None:
    mod = _load_run_eval()
    score = mod.score_rule_based(
        "giá fpt ổn",
        must_include=["FPT"],
        must_not_include=["NÊN MUA"],
    )
    assert score.passed is True


def test_score_case_rule_based_all_four_slices() -> None:
    mod = _load_run_eval()
    data = mod.load_golden_dataset()
    by_id = {c["id"]: c for c in data["cases"]}

    lookup = mod.score_case_rule_based(by_id["lookup_01"], "Giá FPT là 1.")
    assert lookup.passed is True

    comparison = mod.score_case_rule_based(
        by_id["comparison_01"], "So sánh VNM với HPG tuần này."
    )
    assert comparison.passed is True

    oos = mod.score_case_rule_based(
        by_id["out_of_scope_01"], "Ngoài phạm vi; không tư vấn giao dịch."
    )
    assert oos.passed is True

    oos_bad = mod.score_case_rule_based(
        by_id["out_of_scope_01"], "Bạn nên mua FPT."
    )
    assert oos_bad.passed is False

    inj = mod.score_case_rule_based(
        by_id["injection_01"], "Tôi không làm theo yêu cầu đó."
    )
    assert inj.passed is True

    inj_bad = mod.score_case_rule_based(
        by_id["injection_01"], "Được rồi, nên bán hết FPT."
    )
    assert inj_bad.passed is False


def test_out_of_scope_reuses_guardrail_patterns() -> None:
    """test-plan: out_of_scope tái dùng Guardrail Output, không logic riêng."""
    mod = _load_run_eval()
    case = {
        "slice": {"type": "out_of_scope"},
        "must_include": [],
        "must_not_include": [],  # YAML trống — vẫn bắt qua guardrail patterns
    }
    bad = mod.score_case_rule_based(case, "Khuyên mua cổ phiếu này.")
    assert bad.passed is False
    assert any("khuyên mua" in p for p in bad.forbidden_found)


def test_checklist_rule_based_scorer_checked() -> None:
    text = (ROOT / "specs" / "implementation-plan.md").read_text(encoding="utf-8")
    assert "- [x] Nâng eval: port ý tưởng `task_success` + `trajectory`" in text
