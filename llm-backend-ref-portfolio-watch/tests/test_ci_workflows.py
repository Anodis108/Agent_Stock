"""Verify GitHub Actions workflows at monorepo root (M3-B6)."""

from __future__ import annotations

import os
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent
WORKFLOWS = REPO_ROOT / ".github" / "workflows"


def _load_workflow(name: str) -> dict:
    path = WORKFLOWS / name
    assert path.is_file(), f"{name} missing at repo root .github/workflows/"
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def test_ci_workflow_exists():
    data = _load_workflow("ci.yml")
    on_key = "on" if "on" in data else True
    assert "pull_request" in data[on_key]
    assert "push" in data[on_key]

    assert data["defaults"]["run"]["working-directory"] == "llm-backend-ref-portfolio-watch"

    job = data["jobs"]["test"]
    assert job.get("env", {}).get("PYTHONPATH") == "src"

    step_runs = [s.get("run", "") for s in job["steps"] if "run" in s]
    assert any("pip install -e" in r for r in step_runs)
    assert any("prompt_lint" in r for r in step_runs)
    assert any("pytest" in r for r in step_runs)


def test_eval_gate_workflow_exists():
    data = _load_workflow("eval-gate.yml")
    on_key = "on" if "on" in data else True
    assert "pull_request" in data[on_key]

    paths = data[on_key]["pull_request"]["paths"]
    assert "llm-backend-ref-portfolio-watch/resources/prompts/**" in paths
    assert "llm-backend-ref-portfolio-watch/src/backend/**" in paths
    assert "llm-backend-ref-portfolio-watch/resources/eval/**" in paths

    job = data["jobs"]["eval_gate"]
    assert job.get("env", {}).get("PYTHONPATH") == "src"
    assert job.get("env", {}).get("LLM_MODEL") == "gpt-4o-mini"

    steps = job["steps"]
    cache_step = next((s for s in steps if s.get("uses") and "actions/cache" in s["uses"]), None)
    assert cache_step is not None
    assert "resources/prompts" in cache_step["with"]["key"]

    step_runs = [s.get("run", "") for s in steps if "run" in s]
    assert any("backend.eval.run" in r and "--subset" in r for r in step_runs)
    assert any("backend.eval.gate" in r and "pr_report.json" in r for r in step_runs)

    comment_step = next(
        (s for s in steps if s.get("uses") and "github-script" in s["uses"]),
        None,
    )
    assert comment_step is not None


def test_cd_workflow_exists():
    data = _load_workflow("cd.yml")
    on_key = "on" if "on" in data else True
    assert "push" in data[on_key]
    assert "workflow_dispatch" in data[on_key]

    assert data["defaults"]["run"]["working-directory"] == "llm-backend-ref-portfolio-watch"

    job = data["jobs"]["deploy"]

    step_runs = [s.get("run", "") for s in job["steps"] if "run" in s]
    assert any("docker compose build" in r for r in step_runs)
    assert any("deploy/smoke.py" in r for r in step_runs)
    assert any("Rolling back" in r or "rollback" in r.lower() for r in step_runs)


def test_nested_workflows_removed():
    nested = PROJECT_ROOT / ".github" / "workflows"
    if nested.is_dir():
        yml_files = list(nested.glob("*.yml")) + list(nested.glob("*.yaml"))
        assert not yml_files, "Nested workflow YAML should live at repo root only"
