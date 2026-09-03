"""Shim — chuyển sang `tests/run_agent_pr_questions.py`.

Giữ đường dẫn cũ trong REPORT / docs:

    python tests/.run/run_questions.py
    python tests/.run/run_questions.py --sections 16,18 --fresh
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

_TARGET = Path(__file__).resolve().parents[1] / "run_agent_pr_questions.py"

if __name__ == "__main__":
    sys.argv[0] = str(_TARGET)
    runpy.run_path(str(_TARGET), run_name="__main__")
