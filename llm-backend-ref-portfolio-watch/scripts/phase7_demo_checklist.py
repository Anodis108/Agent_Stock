#!/usr/bin/env python3
"""In checklist demo local Phase 7 (localhost, khong can ngrok).

    python scripts/phase7_demo_checklist.py
"""

from __future__ import annotations

import sys


CHECKLIST = """
Phase 7 — Demo local checklist (localhost only, no public tunnel)

Prerequisites:
  Terminal 1: python scripts/serve_ai.py          # :8001
  Terminal 2: python scripts/serve_backend.py     # :8000
  Terminal 3: python scripts/serve_frontend.py    # :5173
  Open http://127.0.0.1:5173/   (NOT ngrok / public URL)

UI checklist:
  [ ] 1. Seed watchlist: FPT (auto-seed if DB empty) or Add on UI / curl POST /watchlist
  [ ] 2. Chat: "Gia FPT hom nay?" -> Timeline has steps (done) + final answer
  [ ] 3. Scan symbol FPT (or added) -> Timeline updates; watchlist still has symbol
  [ ] 4. If Approvals pending -> Approve (or Reject + reason); else skip

API smoke (mocked AI, no browser):
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
