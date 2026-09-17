"""Phase 7 — docker-compose.yml: service app, port map, SQLite volume."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_docker_compose_has_app_port_and_sqlite_volume():
    path = ROOT / "docker-compose.yml"
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    assert "services:" in text
    assert "app:" in text
    assert "build:" in text or "image:" in text
    assert "8000:8000" in text or '"8000:8000"' in text or "APP_HOST_PORT" in text
    assert "volumes:" in text
    assert "/app/data" in text
    assert "SQLITE_PATH" in text
    assert "portfolio_watch.db" in text or "sqlite" in text.lower()
    # Không hard-code API key trong compose
    assert "sk-" not in text.lower()
    assert "OPENAI_API_KEYS=sk" not in text
