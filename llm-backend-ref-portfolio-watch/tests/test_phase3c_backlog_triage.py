"""Phase 3c — backlog triage: không có gap mới khi blocked rỗng."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "specs" / "implementation-plan.md"
BLOCKED = ROOT / "specs" / "eval" / "blocked_cases.yaml"


def test_phase3c_backlog_triaged_when_blocked_empty():
    blocked_doc = yaml.safe_load(BLOCKED.read_text(encoding="utf-8")) or {}
    blocked = blocked_doc.get("blocked") or []
    assert blocked == [], "có blocked case → phải thêm task Phase 3c, không chỉ triage"

    plan = PLAN.read_text(encoding="utf-8")
    start = plan.index("**3c — Backlog multi-agent**")
    end = plan.index("## Phase 4")
    block = plan[start:end]
    assert "blocked_cases.yaml" in block
    assert "Rà soát backlog" in block or "không có gap" in block
    # Placeholder italic unchecked không còn là item mở
    assert "- [ ] _Thêm task mới" not in block
    # Quy trình thêm task khi fail vẫn ghi rõ (không xóa cửa sổ backlog)
    assert "blocked_cases.yaml" in block
    assert "- [ ]" not in block or "Khi case fail" in block
