"""Phase 7 — xác nhận Docker Compose / 3 luồng smoke helpers."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_verify_clean_docker_script_exists():
    script = ROOT / "scripts" / "verify_clean_docker.py"
    assert script.is_file()
    text = script.read_text(encoding="utf-8")
    assert "CLEAN_DOCKER_SMOKE_OK" in text
    assert "docker" in text and "compose" in text
    assert "/scan" in text and "/chat" in text and "/approvals" in text
    assert "up" in text and "--build" in text


def test_readme_mentions_docker_verify_script():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "scripts/verify_clean_docker.py" in readme
    assert "CLEAN_DOCKER_SMOKE_OK" in readme
