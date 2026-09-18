"""Phase 7 — README + script kịch bản demo local."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
SCRIPT = ROOT / "scripts" / "phase7_demo_checklist.py"


def test_readme_phase7_demo_local_scenario():
    text = README.read_text(encoding="utf-8")
    assert "Demo with local" in text
    assert "127.0.0.1:5173" in text
    assert "ngrok" in text.lower()
    assert "BACKEND_BASE_URL" in text or "config.js" in text
    assert "watchlist" in text.lower()
    assert "Timeline" in text or "timeline" in text
    assert "Giá FPT" in text or "FPT hôm nay" in text
    assert "/watchlist" in text
    assert "phase7_demo_checklist.py" in text
    assert "Approvals" in text or "duyệt" in text.lower()


def test_phase7_demo_checklist_script_prints_steps():
    assert SCRIPT.is_file()
    out = subprocess.check_output(
        [sys.executable, str(SCRIPT)],
        cwd=str(ROOT),
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert "Phase 7" in out
    assert "5173" in out
    assert "watchlist" in out.lower()
    assert "Chat" in out or "chat" in out
    assert "Scan" in out or "scan" in out
    assert "Approve" in out or "approvals" in out.lower()
    assert "ngrok" in out.lower()
