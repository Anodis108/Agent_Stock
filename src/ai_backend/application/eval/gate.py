#!/usr/bin/env python3
"""CLI entry — canonical gate logic in `ai_backend.infra.eval.gate`.

    python -m ai_backend.application.eval.gate --run resources/eval/pr_report.json
"""

from __future__ import annotations

from ai_backend.infra.eval.gate import (  # noqa: F401
    GATES,
    GateCheck,
    GateResult,
    check_gates,
    format_gate_result,
    load_gate_report,
    main,
    normalize_gate_report,
)

if __name__ == "__main__":
    raise SystemExit(main())
