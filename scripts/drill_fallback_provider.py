#!/usr/bin/env python3
"""Drill: in cấu hình LLM backend (fallback provider cascade đã gỡ khỏi infra/llm)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from common.settings.config import settings  # noqa: E402


def main() -> int:
    print(f"LLM backend: {settings.llm_backend}")
    print(f"LLM model:   {settings.llm_model}")
    if settings.llm_fallback_backends.strip():
        print(
            "NOTE: LLM_FALLBACK_BACKENDS is set but no longer used by completion — "
            "chỉ một backend như llm-engineer-demo."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
