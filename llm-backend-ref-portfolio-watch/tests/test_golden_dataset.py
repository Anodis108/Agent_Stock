"""Phase 9 — golden_dataset.yaml schema and slice ratios (18/6/3/3)."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "specs" / "eval" / "golden_dataset.yaml"

REQUIRED_CASE_KEYS = {
    "id",
    "question",
    "expected",
    "slice",
    "must_include",
    "must_not_include",
}
EXPECTED_COUNTS = {
    "lookup": 18,
    "comparison": 6,
    "out_of_scope": 3,
    "injection": 3,
}


def _load() -> dict:
    assert GOLDEN.is_file(), f"missing {GOLDEN}"
    data = yaml.safe_load(GOLDEN.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def test_golden_dataset_top_level_metadata() -> None:
    data = _load()
    for key in ("dataset", "version", "created", "changelog", "cases"):
        assert key in data, f"missing dataset-level key {key}"
    assert data["dataset"]
    assert data["version"]
    assert data["created"]
    assert str(data["changelog"]).strip()
    assert isinstance(data["cases"], list)
    assert len(data["cases"]) == 30


def test_golden_dataset_case_schema_and_slice_ratio() -> None:
    data = _load()
    counts: dict[str, int] = {k: 0 for k in EXPECTED_COUNTS}
    ids: list[str] = []

    for case in data["cases"]:
        assert REQUIRED_CASE_KEYS <= set(case.keys()), case
        assert isinstance(case["id"], str) and case["id"]
        assert isinstance(case["question"], str) and case["question"].strip()
        assert isinstance(case["expected"], str) and case["expected"].strip()
        assert isinstance(case["must_include"], list)
        assert isinstance(case["must_not_include"], list)
        sl = case["slice"]
        assert isinstance(sl, dict)
        assert "type" in sl and "multihop" in sl
        assert isinstance(sl["multihop"], bool)
        st = sl["type"]
        assert st in EXPECTED_COUNTS, st
        counts[st] += 1
        ids.append(case["id"])
        if st == "comparison":
            assert sl["multihop"] is True
        if st == "lookup":
            assert sl["multihop"] is False

    assert counts == EXPECTED_COUNTS
    assert len(ids) == len(set(ids)), "duplicate case ids"


def test_out_of_scope_and_injection_reuse_guardrail_phrases() -> None:
    """test-plan: out_of_scope/injection must_not_include khớp Guardrail Output."""
    data = _load()
    required = {"nên mua", "nên bán"}
    for case in data["cases"]:
        if case["slice"]["type"] not in ("out_of_scope", "injection"):
            continue
        phrases = {p.lower() for p in case["must_not_include"]}
        assert required <= phrases, case["id"]


def test_golden_dataset_checklist_item_checked() -> None:
    text = (ROOT / "specs" / "implementation-plan.md").read_text(encoding="utf-8")
    assert (
        "- [x] `specs/eval/golden_dataset.yaml` — 30 case theo tỉ lệ 18/6/3/3"
        in text
    )
