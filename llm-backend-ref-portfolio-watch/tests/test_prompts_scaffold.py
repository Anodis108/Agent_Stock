"""Phase 8 item 1 — khung prompts/ (v1.yaml + production.txt) đúng spec."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
PROMPTS = ROOT / "prompts"

REQUIRED_DIRS = (
    "event_classification",
    "eval_severity",
    "synthesis_alert",
    "supervisor_routing",
    "rewrite_question",
    "answer_compose",
    "news_agent_react",
)

REQUIRED_FIELDS = (
    "name",
    "version",
    "model",
    "description",
    "owner",
    "created",
    "changelog",
    "eval_score",
    "template",
)


def test_prompts_scaffold_has_seven_agent_dirs():
    assert PROMPTS.is_dir(), f"missing {PROMPTS}"
    for name in REQUIRED_DIRS:
        d = PROMPTS / name
        assert d.is_dir(), f"missing prompts/{name}/"
        assert (d / "v1.yaml").is_file(), f"missing prompts/{name}/v1.yaml"
        assert (d / "production.txt").is_file(), f"missing prompts/{name}/production.txt"


def test_production_txt_points_to_version_1():
    for name in REQUIRED_DIRS:
        raw = (PROMPTS / name / "production.txt").read_text(encoding="utf-8").strip()
        assert raw == "1", f"{name}/production.txt expected '1', got {raw!r}"


def test_v1_yaml_has_required_metadata_and_dollar_vars():
    for name in REQUIRED_DIRS:
        data = yaml.safe_load((PROMPTS / name / "v1.yaml").read_text(encoding="utf-8"))
        assert isinstance(data, dict), name
        for field in REQUIRED_FIELDS:
            assert field in data, f"{name}: missing field {field}"
        assert data["name"] == name
        assert data["version"] == 1
        assert str(data.get("changelog") or "").strip(), f"{name}: changelog rỗng"
        assert isinstance(data["template"], str) and data["template"].strip()
        # string.Template style — ít nhất 1 biến $... trong template MVP
        assert "$" in data["template"], f"{name}: template nên dùng $var"


def test_pyyaml_is_declared_dependency():
    """prompts/*.yaml cần PyYAML lúc parse (test + PromptRegistry sắp tới)."""
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8").lower()
    assert "pyyaml" in text
