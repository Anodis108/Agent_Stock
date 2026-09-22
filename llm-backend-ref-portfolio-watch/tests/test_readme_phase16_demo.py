"""Phase 16 line 5 — README demo walkthrough."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_readme_has_demo_walkthrough():
    content = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "## Demo walkthrough" in content

    demo_section = content.split("## Demo walkthrough")[1].split("\n## ")[0].lower()

    assert "chat" in demo_section
    assert "graph" in demo_section or "hover" in demo_section
    assert "market" in demo_section
    assert "langfuse" in demo_section
    assert "optional" in demo_section or "tuỳ chọn" in demo_section or "tùy chọn" in demo_section
