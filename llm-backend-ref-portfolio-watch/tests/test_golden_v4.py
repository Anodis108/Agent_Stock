"""Golden dataset v4 — schema & test case validation for Phase 7 (30 cases chuẩn hóa)."""

from __future__ import annotations

from pathlib import Path
import yaml
import pytest

ROOT = Path(__file__).resolve().parents[1]
GOLDEN_V4_RESOURCE = ROOT / "resources" / "eval" / "golden_v4.yaml"
GOLDEN_V4_SPECS = ROOT / "specs" / "eval" / "golden_v4.yaml"


@pytest.mark.parametrize("file_path", [GOLDEN_V4_RESOURCE, GOLDEN_V4_SPECS])
def test_golden_v4_structure_and_counts(file_path: Path):
    """Kiểm tra tính toàn vẹn và phân bổ 30 cases của Golden Dataset v4."""
    assert file_path.is_file(), f"File không tồn tại: {file_path}"

    data = yaml.safe_load(file_path.read_text(encoding="utf-8"))
    assert data.get("dataset") == "portfolio_watch"
    assert str(data.get("version")) == "4"
    assert data.get("changelog"), "Phải có trường changelog"

    cases = data.get("cases", [])
    assert len(cases) == 30, f"Golden Dataset v4 bắt buộc phải có đúng 30 cases, hiện tại có {len(cases)}"

    ids: set[str] = set()
    slice_counts = {
        "lookup": 0,
        "comparison": 0,
        "charting_diagram": 0,
        "session_memory": 0,
        "out_of_scope": 0,
        "injection": 0,
    }

    for case in cases:
        case_id = case.get("id")
        assert case_id, "Case thiếu trường id"
        assert case_id not in ids, f"Trùng lặp case id: {case_id}"
        ids.add(case_id)

        assert case.get("question"), f"Case {case_id} thiếu câu hỏi (question)"
        assert case.get("expected"), f"Case {case_id} thiếu kết quả mong đợi (expected)"

        slice_data = case.get("slice") or {}
        slice_type = slice_data.get("type")
        assert slice_type in slice_counts, f"Case {case_id} có slice.type không hợp lệ: {slice_type}"
        slice_counts[slice_type] += 1

        assert slice_data.get("difficulty") in {"easy", "medium", "hard"}, (
            f"Case {case_id} có độ khó không hợp lệ"
        )

        assert isinstance(case.get("must_include", []), list), f"Case {case_id}: must_include phải là list"
        assert isinstance(case.get("must_not_include", []), list), f"Case {case_id}: must_not_include phải là list"

    # Kiểm tra số lượng phân bổ theo đúng đặc tả Phase 7
    assert slice_counts["lookup"] == 12, f"Expected 12 lookup cases, got {slice_counts['lookup']}"
    assert slice_counts["comparison"] == 6, f"Expected 6 comparison cases, got {slice_counts['comparison']}"
    assert slice_counts["charting_diagram"] == 4, f"Expected 4 charting_diagram cases, got {slice_counts['charting_diagram']}"
    assert slice_counts["session_memory"] == 2, f"Expected 2 session_memory cases, got {slice_counts['session_memory']}"
    assert slice_counts["out_of_scope"] == 3, f"Expected 3 out_of_scope cases, got {slice_counts['out_of_scope']}"
    assert slice_counts["injection"] == 3, f"Expected 3 injection cases, got {slice_counts['injection']}"


def test_golden_v4_guardrails_rules():
    """Kiểm tra các quy tắc guardrails và must_not_include trong golden_v4.yaml."""
    data = yaml.safe_load(GOLDEN_V4_RESOURCE.read_text(encoding="utf-8"))
    cases = data.get("cases", [])

    for case in cases:
        slice_type = case.get("slice", {}).get("type")

        # Tất cả các case phải có ràng buộc chống tư vấn mua/bán tùy tiện
        must_not_include = [w.lower() for w in case.get("must_not_include", [])]
        assert "nên mua" in must_not_include, f"Case {case['id']} thiếu ràng buộc cấm 'nên mua'"
        assert "nên bán" in must_not_include, f"Case {case['id']} thiếu ràng buộc cấm 'nên bán'"

        # Injection slice kiểm tra chặt chẽ
        if slice_type == "injection":
            assert len(must_not_include) >= 2
