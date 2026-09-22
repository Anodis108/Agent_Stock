"""Golden dataset v3 — schema Class 18 (Phase 15)."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
GOLDEN_V3 = ROOT / "specs" / "eval" / "golden_v3.yaml"


def test_golden_v3_structure():
    assert GOLDEN_V3.is_file(), f"File not found: {GOLDEN_V3}"

    data = yaml.safe_load(GOLDEN_V3.read_text(encoding="utf-8"))

    assert data.get("dataset") == "portfolio_watch"
    assert str(data.get("version")) == "3"
    assert data.get("changelog"), "changelog required"

    cases = data.get("cases", [])
    assert len(cases) >= 33, f"Expected at least 33 cases, got {len(cases)}"

    ids: set[str] = set()
    slice_types = {"lookup": 0, "comparison": 0, "out_of_scope": 0, "injection": 0, "diagram": 0}

    for case in cases:
        case_id = case.get("id")
        assert case_id, "Case missing id"
        assert case_id not in ids, f"Duplicate id: {case_id}"
        ids.add(case_id)

        slice_data = case.get("slice") or {}
        slice_type = slice_data.get("type")
        assert slice_type, f"Case {case_id} missing slice.type"
        assert slice_data.get("difficulty") in {"easy", "medium", "hard"}, (
            f"Case {case_id} missing valid slice.difficulty"
        )

        if slice_type in slice_types:
            slice_types[slice_type] += 1
        else:
            slice_types[slice_type] = 1

    assert slice_types["lookup"] >= 18
    assert slice_types["comparison"] >= 6
    assert slice_types["out_of_scope"] >= 3
    assert slice_types["injection"] >= 3
    assert slice_types["diagram"] >= 3
    assert set(slice_types.keys()) == {
        "lookup",
        "comparison",
        "out_of_scope",
        "injection",
        "diagram",
    }

    for case in cases:
        if case.get("slice", {}).get("type") != "diagram":
            continue
        assert case.get("must_include"), f"{case['id']} missing must_include"
        assert case.get("must_not_include"), f"{case['id']} missing must_not_include"
