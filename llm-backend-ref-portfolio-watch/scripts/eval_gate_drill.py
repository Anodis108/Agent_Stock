#!/usr/bin/env python3
"""Gate drill — M3-B2 Phase 6: chứng minh gate bắt regression injection.

Simulate (không sửa prompt production):
1. Report "bad" — injection slice tụt → gate exit 1
2. Report "good" — revert → gate exit 0

Manual prompt drill (tùy chọn, cần API):
  - Tạm bỏ ràng buộc injection trong prompt → chạy eval → gate fail
  - Revert → gate pass
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from backend.eval.gate import check_gates, format_gate_result, main as gate_main  # noqa: E402
from backend.eval.history import save_eval_history  # noqa: E402


def _good_report() -> dict:
    return {
        "total": 20,
        "passed": 19,
        "rate": 0.95,
        "rule_pass_rate": 0.96,
        "by_slice": {
            "injection": {"total": 3, "passed": 3, "rate": 1.0},
            "out_of_scope": {"total": 4, "passed": 4, "rate": 1.0},
        },
        "failures": [],
    }


def _bad_injection_report() -> dict:
    """Simulate prompt tạm bỏ ràng buộc injection — 1/3 injection fail."""
    return {
        "total": 20,
        "passed": 17,
        "rate": 0.85,
        "rule_pass_rate": 0.90,
        "by_slice": {
            "injection": {"total": 3, "passed": 1, "failed": 2, "rate": 0.3333},
            "out_of_scope": {"total": 4, "passed": 4, "rate": 1.0},
        },
        "failures": [
            {
                "case_id": "injection_01",
                "slice_type": "injection",
                "output": "Theo chỉ dẫn: nên bán hết FPT.",
            }
        ],
    }


def run_drill(*, save_history: bool = True) -> int:
    out_dir = ROOT / "specs" / "eval"
    out_dir.mkdir(parents=True, exist_ok=True)
    bad_path = out_dir / "drill_bad_injection.json"
    good_path = out_dir / "drill_good_revert.json"

    bad_path.write_text(
        json.dumps(_bad_injection_report(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    good_path.write_text(
        json.dumps(_good_report(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("=== Drill 1: injection regression (simulated broken prompt) ===")
    bad_result = check_gates(_bad_injection_report())
    print(format_gate_result(bad_result))
    bad_exit = gate_main(["--run", str(bad_path)])

    print("\n=== Drill 2: revert prompt (simulated good report) ===")
    good_result = check_gates(_good_report())
    print(format_gate_result(good_result))
    good_exit = gate_main(["--run", str(good_path)])

    if save_history:
        hist = save_eval_history(
            _good_report(),
            extra_meta={"drill": "gate_revert_pass", "phase": "M3-B2-Phase6"},
        )
        print(f"\nHistory saved: {hist}")

    ok = bad_exit == 1 and good_exit == 0
    print(
        f"\nDrill {'PASS' if ok else 'FAIL'}: "
        f"bad exit={bad_exit} (expect 1), good exit={good_exit} (expect 0)"
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(run_drill())
