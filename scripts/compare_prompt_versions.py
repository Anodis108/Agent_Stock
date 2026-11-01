#!/usr/bin/env python3
"""So sánh system prompt v1 vs v2 — M3-B1 (rewrite_question, answer_compose)."""

from __future__ import annotations

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

from ai_backend.infra.prompts import registry  # noqa: E402

SEP = "-" * 72


def _print_pair(title: str, v1: str, v2: str) -> None:
    print(f"\n{SEP}\n{title}\n{SEP}")
    print("[v1]")
    print(v1.strip())
    print("\n[v2]")
    print(v2.strip())
    print()


def main() -> int:
    reg = registry()
    for name in ("rewrite_question", "answer_compose"):
        print(f"=== {name}: v1 vs v2 (system template) ===")
        v1 = reg.get(name, version=1).template
        v2 = reg.get(name, version=2).template
        _print_pair(name, v1, v2)
        prod = reg.get(name, version="production").template
        print(f"production alias → matches v1: {prod.strip() == v1.strip()}")
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
