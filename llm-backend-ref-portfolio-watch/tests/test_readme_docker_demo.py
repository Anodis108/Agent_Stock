"""Phase 7 — README mục Demo bằng Docker (3 service) đủ checklist."""

from __future__ import annotations

from pathlib import Path

README = Path(__file__).resolve().parents[1] / "README.md"


def test_readme_docker_demo_section():
    text = README.read_text(encoding="utf-8")
    assert "## Demo bằng Docker" in text
    assert "Docker" in text and "Compose" in text
    assert ".env.example" in text
    assert "docker compose up --build" in text
    assert "docker compose down" in text
    assert "logs" in text
    assert "8001" in text and "8000" in text and "5173" in text
    assert "ai" in text and "backend" in text and "frontend" in text
    assert "-v" in text or "volume" in text.lower() or "pw_data" in text
    assert "/app/data" in text or "portfolio-watch-data" in text
