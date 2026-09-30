#!/usr/bin/env python3
"""Drill: kiểm tra fallback provider chain (Module III Bài 7)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from backend.infra.llm.providers import resolve_backend_chain  # noqa: E402
from backend.shared.settings import settings  # noqa: E402


def main() -> int:
    chain = resolve_backend_chain()
    print(f"Primary backend: {settings.llm_backend}")
    print(f"Fallback chain:  {chain}")
    if len(chain) < 2 and settings.llm_fallback_backends.strip():
        print("WARN: LLM_FALLBACK_BACKENDS set but chain has only 1 entry")
    if len(chain) >= 2:
        print("OK: fallback configured")
        return 0
    print("INFO: no fallback backends — set LLM_FALLBACK_BACKENDS=ollama,openai")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
