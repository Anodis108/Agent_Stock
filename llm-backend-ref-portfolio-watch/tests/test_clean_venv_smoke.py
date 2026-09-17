"""Phase 6 — xác nhận clean venv / README smoke helpers."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_verify_clean_local_script_exists():
    script = ROOT / "scripts" / "verify_clean_local.py"
    assert script.is_file()
    text = script.read_text(encoding="utf-8")
    assert "CLEAN_VENV_SMOKE_OK" in text
    assert "/scan" in text and "/chat" in text and "/approvals" in text
    assert "pip" in text and "venv" in text


def test_settings_env_overrides_dotenv_file(tmp_path):
    """Biến môi trường phải thắng nội dung .env (máy sạch / SQLITE_PATH tạm)."""
    isolated = tmp_path / "isolated.db"
    env = {**os.environ, "SQLITE_PATH": str(isolated), "OPENAI_API_KEYS": "not-needed"}
    out = subprocess.check_output(
        [
            sys.executable,
            "-c",
            "from src.portfolio_watch.shared.settings import settings; print(settings.sqlite_path)",
        ],
        cwd=str(ROOT),
        env=env,
        text=True,
    ).strip()
    assert out == str(isolated)


def test_readme_mentions_clean_verify_script():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "scripts/verify_clean_local.py" in readme
    assert "CLEAN_VENV_SMOKE_OK" in readme


def test_settings_load_dotenv_override_false():
    src = (ROOT / "src/portfolio_watch/shared/settings.py").read_text(encoding="utf-8")
    assert "override=False" in src
