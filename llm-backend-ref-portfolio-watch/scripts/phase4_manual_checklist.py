#!/usr/bin/env python3
"""In checklist kiem thu tay Phase 4 (UI steps + pytest smoke).

    python scripts/phase4_manual_checklist.py
"""

from __future__ import annotations

import sys


CHECKLIST = """
Phase 4 — Manual checklist (3 processes)

Prerequisites:
  Terminal 1: python scripts/serve_ai.py          # :8001
  Terminal 2: python scripts/serve_backend.py     # :8000
  Terminal 3: python scripts/serve_frontend.py    # :5173
  Open http://127.0.0.1:5173/

UI checklist:
  [ ] 1. Chat: ask "Gia FPT?" -> Timeline has steps (done) + Chat shows final answer
  [ ] 2. Watchlist: Add symbol (e.g. HPG) + threshold -> row appears
  [ ] 3. Scan that symbol -> Timeline updates from Backend steps
  [ ] 4. If pending approval -> Approve (or Reject + reason) -> list empty

API smoke (same flow, mocked AI):
  python -m pytest tests/test_phase4_manual_checklist.py -q
""".strip()


def main() -> int:
    data = (CHECKLIST + "\n").encode("utf-8", errors="replace")
    buf = getattr(sys.stdout, "buffer", None)
    if buf is not None:
        buf.write(data)
        buf.flush()
    else:
        sys.stdout.write(CHECKLIST + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
