"""Phase 17 line 1 — README optional local development appendix."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_readme_has_optional_local_development():
    content = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "## Optional local development" in content

    docker_idx = content.index("## Quick Start")
    local_idx = content.index("## Optional local development")
    assert docker_idx < local_idx, "Docker-first must precede local appendix"

    local_section = content.split("## Optional local development")[1].split("\n## ")[0].lower()

    assert "uvicorn backend.backend.main" in local_section
    assert "pytest" in local_section
    assert "pip install -e" in local_section
    assert "localhost:8000" in local_section
    assert "docker" in content.split("## Optional local development")[0].lower()
