"""Phase 7 — Dockerfile tồn tại và đủ checklist (deps, web/, expose 8000, uvicorn)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_dockerfile_covers_phase7_first_item():
    df = ROOT / "Dockerfile"
    assert df.is_file()
    text = df.read_text(encoding="utf-8")
    assert "FROM python:" in text
    assert "pip install" in text
    assert "-e ." in text or "pip install --no-cache-dir -e ." in text
    assert "COPY src" in text or "COPY ./src" in text
    assert "COPY web" in text or "COPY ./web" in text
    assert "COPY prompts" in text or "COPY ./prompts" in text
    assert "EXPOSE 8000" in text
    assert "uvicorn" in text
    assert "src.portfolio_watch.main:app" in text
    assert "0.0.0.0" in text
    # Không bake secret vào image
    assert "sk-" not in text.lower()
    assert "OPENAI_API_KEYS=sk" not in text


def test_dockerignore_excludes_env_and_venv():
    ignore = (ROOT / ".dockerignore").read_text(encoding="utf-8")
    assert ".env" in ignore
    assert ".venv" in ignore or "venv" in ignore
