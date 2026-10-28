"""Golden dataset loader & validator — map `app/eval_pipeline/dataset.py`.

vn-stock: YAML `resources/eval/golden_dataset*.yaml` + blocked cases.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from ai_backend.infra.eval.scorers import RULE_SLICES
from pydantic import BaseModel


def _find_project_root() -> Path:
    p = Path(__file__).resolve().parent
    for _ in range(6):
        if (p / "specs").is_dir() or (p / "pyproject.toml").is_file():
            return p
        p = p.parent
    return Path(__file__).resolve().parents[4]


ROOT = _find_project_root()
GOLDEN_PATH = ROOT / "resources" / "eval" / "golden_dataset.yaml"
EXTENDED_DATASET_PATH = ROOT / "resources" / "eval" / "extended_dataset.yaml"
GOLDEN_V3_PATH = ROOT / "resources" / "eval" / "golden_v3.yaml"
GOLDEN_V4_PATH = ROOT / "resources" / "eval" / "golden_v4.yaml"
GOLDEN_V5_PATH = (
    EXTENDED_DATASET_PATH
    if EXTENDED_DATASET_PATH.is_file()
    else (ROOT / "resources" / "eval" / "golden_v5.yaml")
)
GOLDEN_V6_PATH = (
    GOLDEN_PATH
    if GOLDEN_PATH.is_file()
    else (ROOT / "resources" / "eval" / "golden_v6_comprehensive.yaml")
)
CI_DATASET_PATH = (
    ROOT / "resources" / "eval" / "ci_dataset.yaml"
    if (ROOT / "resources" / "eval" / "ci_dataset.yaml").is_file()
    else ROOT / "resources" / "eval" / "golden_pr_subset.yaml"
)
GOLDEN_PR_SUBSET_PATH = CI_DATASET_PATH
BASELINE_PATH = (
    ROOT / "resources" / "eval" / "golden_baseline.json"
    if (ROOT / "resources" / "eval" / "golden_baseline.json").is_file()
    else (
        ROOT / "resources" / "eval" / "v6_baseline.json"
        if (ROOT / "resources" / "eval" / "v6_baseline.json").is_file()
        else (
            ROOT / "resources" / "eval" / "extended_baseline.json"
            if (ROOT / "resources" / "eval" / "extended_baseline.json").is_file()
            else (
                ROOT / "resources" / "eval" / "v5_baseline.json"
                if (ROOT / "resources" / "eval" / "v5_baseline.json").is_file()
                else ROOT / "resources" / "eval" / "baseline.json"
            )
        )
    )
)
BLOCKED_PATH = ROOT / "resources" / "eval" / "blocked_cases.yaml"


class BlockedCase(BaseModel):
    id: str
    reason: str
    phase3c_task: str
    since: str = ""

    def as_dict(self) -> dict:
        return self.model_dump()


def load_blocked_cases(path: Path | None = None) -> list[BlockedCase]:
    """Đọc resources/eval/blocked_cases.yaml — case fail đã ghi nhận + task 3c."""
    p = path or BLOCKED_PATH
    if not p.is_file():
        return []
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    raw = data.get("blocked") or []
    out: list[BlockedCase] = []
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError(f"blocked entry phải là object: {item!r}")
        cid = str(item.get("id") or "").strip()
        reason = str(item.get("reason") or "").strip()
        task = str(item.get("phase3c_task") or "").strip()
        if not cid or not reason or not task:
            raise ValueError(
                "blocked entry thiếu id/reason/phase3c_task — "
                "không được ghi blocked nửa vời"
            )
        out.append(
            BlockedCase(
                id=cid,
                reason=reason,
                phase3c_task=task,
                since=str(item.get("since") or ""),
            )
        )
    return out


def validate_golden_case_rules(case: dict) -> None:
    """Kiểm tra case phải có must_include và must_not_include là list."""
    cid = case.get("id") or "unknown"
    if "must_include" not in case or not isinstance(case["must_include"], list):
        raise ValueError(f"Case {cid} thiếu must_include (phải là list)")
    if "must_not_include" not in case or not isinstance(case["must_not_include"], list):
        raise ValueError(f"Case {cid} thiếu must_not_include (phải là list)")
    slice_type = (case.get("slice") or {}).get("type")
    if slice_type and slice_type not in RULE_SLICES:
        raise ValueError(f"Case {cid} slice.type={slice_type!r} không thuộc RULE_SLICES")


def resolve_golden_cases(data: dict, *, base_dir: Path) -> list[dict]:
    """Trả về danh sách case — hỗ trợ subset tham chiếu `case_ids` + `source`."""
    if "cases" in data:
        cases = data["cases"]
        if not isinstance(cases, list):
            raise ValueError("Trường 'cases' phải là list")
        return cases
    case_ids = data.get("case_ids")
    if not isinstance(case_ids, list) or not case_ids:
        raise ValueError("Dataset phải có 'cases' hoặc 'case_ids' không rỗng")
    source_name = str(data.get("source") or "golden_v5.yaml")
    source_path = base_dir / source_name
    if not source_path.is_file():
        raise FileNotFoundError(
            f"Subset source '{source_name}' không tìm thấy tại {source_path}"
        )
    source_data = yaml.safe_load(source_path.read_text(encoding="utf-8"))
    if not isinstance(source_data, dict) or "cases" not in source_data:
        raise ValueError(f"Source dataset không hợp lệ: {source_path}")
    by_id = {str(c.get("id")): c for c in source_data["cases"] if c.get("id")}
    resolved: list[dict] = []
    for cid in case_ids:
        key = str(cid)
        if key not in by_id:
            raise ValueError(
                f"case_id '{key}' không có trong source {source_name}"
            )
        resolved.append(by_id[key])
    return resolved


def load_golden_dataset(path: Path | None = None, validate_rules: bool = False) -> dict:
    p = path
    if p is None:
        if GOLDEN_V6_PATH.is_file():
            p = GOLDEN_V6_PATH
        elif GOLDEN_V5_PATH.is_file():
            p = GOLDEN_V5_PATH
        elif GOLDEN_V4_PATH.is_file():
            p = GOLDEN_V4_PATH
        elif GOLDEN_V3_PATH.is_file():
            p = GOLDEN_V3_PATH
        else:
            p = GOLDEN_PATH
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"invalid golden dataset: {p}")
    cases = resolve_golden_cases(data, base_dir=p.parent)
    data = {**data, "cases": cases}
    validate_names = {
        "golden_dataset.yaml",
        "extended_dataset.yaml",
        "ci_dataset.yaml",
        "golden_v3.yaml",
        "golden_v4.yaml",
        "golden_v5.yaml",
        "golden_v6_comprehensive.yaml",
        "golden_pr_subset.yaml",
    }
    if p.name in validate_names or validate_rules:
        for c in data["cases"]:
            validate_golden_case_rules(c)
            if not str(c.get("expected") or "").strip():
                raise ValueError(f"Case {c.get('id')} thiếu expected")
            if not (c.get("slice") or {}).get("type"):
                raise ValueError(f"Case {c.get('id')} thiếu slice.type")
    return data


def format_fail_policy_guidance(
    failures: list[Any],
    blocked: list[BlockedCase] | None = None,
) -> str:
    """Nhắc policy khi có case fail (Phase 5)."""
    blocked = blocked if blocked is not None else load_blocked_cases()
    blocked_ids = {b.id for b in blocked}
    lines = [
        "=== Eval policy (không nới scorer) ===",
        "Case fail → (1) sửa multi-agent/prompt/tool, hoặc",
        "(2) ghi resources/eval/blocked_cases.yaml + task Phase 3c.",
        "Cấm: hạ JUDGE_PASS_THRESHOLD, nới REGRESSION_TOLERANCE, "
        "xoá must_include chỉ để pass.",
    ]
    if not failures:
        lines.append("Failures: (none)")
        if blocked:
            lines.append(f"Blocked registry: {len(blocked)} case đã ghi nhận.")
        return "\n".join(lines)

    lines.append(f"Failures cần xử lý ({len(failures)}):")
    for f in failures:
        cid = getattr(f, "case_id", str(f))
        tag = " [blocked]" if cid in blocked_ids else " [CHƯA blocked]"
        lines.append(f"  - {cid}{tag}")
    undocumented = [
        getattr(f, "case_id", str(f))
        for f in failures
        if getattr(f, "case_id", str(f)) not in blocked_ids
    ]
    if undocumented:
        lines.append(
            "Chưa blocked: "
            + ", ".join(undocumented)
            + " — sửa hệ thống hoặc thêm entry blocked + Phase 3c."
        )
    else:
        lines.append("Mọi fail đều đã có trong blocked_cases.yaml.")
    return "\n".join(lines)


def format_blocked_registry(blocked: list[BlockedCase] | None = None) -> str:
    blocked = blocked if blocked is not None else load_blocked_cases()
    lines = ["=== Blocked cases registry ==="]
    if not blocked:
        lines.append("(trống — không có case blocked)")
        return "\n".join(lines)
    for b in blocked:
        since = f" since={b.since}" if b.since else ""
        lines.append(
            f"  - [{b.id}]{since}: {b.reason} | 3c: {b.phase3c_task}"
        )
    return "\n".join(lines)
