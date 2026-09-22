"""Phase 16 — README chỉ Docker product + eval trong container."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_readme_docker_product_only():
    content = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "docker compose up --build" in content
    assert "docker compose run --rm app python -m src.portfolio_watch.eval.run" in content
    assert "docker compose run --rm app python -m src.portfolio_watch.eval.regression" in content

    assert "## Chạy local" not in content
    assert "http.server 5173" not in content

    docker_idx = content.index("## Quick Start")
    local_idx = content.find("## Optional local development")
    if local_idx >= 0:
        assert docker_idx < local_idx
        local_section = content[local_idx:].split("\n## ", 1)[0]
        assert "uvicorn src.portfolio_watch.backend.main" in local_section
    else:
        assert "uvicorn src.portfolio_watch.backend.main" not in content
