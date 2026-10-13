"""Rollback production.txt về version trước. Không xoá vN.yaml."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from prompt_rollback import rollback_prompt  # noqa: E402


def _write_prompt(root: Path, name: str, versions: dict[int, str], production: str) -> Path:
    prompt_dir = root / name
    prompt_dir.mkdir(parents=True)
    for version, template in versions.items():
        payload = {
            "name": name,
            "version": version,
            "model": "gpt-4o-mini",
            "owner": "test",
            "changelog": f"v{version}",
            "template": template,
        }
        (prompt_dir / f"v{version}.yaml").write_text(
            yaml.safe_dump(payload, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
    (prompt_dir / "production.txt").write_text(production, encoding="utf-8")
    return prompt_dir


def test_rollback_pointer_keeps_yaml_files(tmp_path: Path):
    prompt_dir = _write_prompt(
        tmp_path,
        "answer_compose",
        {1: "ban v1 $question", 2: "ban v2 $question"},
        "v2\n",
    )
    before = {
        path.name: path.read_bytes()
        for path in prompt_dir.glob("v*.yaml")
    }

    assert rollback_prompt(prompt_dir) == 1
    assert (prompt_dir / "production.txt").read_text(encoding="utf-8") == "v1\n"
    after = {
        path.name: path.read_bytes()
        for path in prompt_dir.glob("v*.yaml")
    }
    assert after == before
    assert set(after) == {"v1.yaml", "v2.yaml"}


def test_rollback_from_template_text(tmp_path: Path):
    prompt_dir = _write_prompt(
        tmp_path,
        "rewrite_question",
        {1: "cu v1 $question", 2: "cu v2 $question"},
        "cu v2 $question\n",
    )
    v2_bytes = (prompt_dir / "v2.yaml").read_bytes()

    assert rollback_prompt(prompt_dir) == 1
    assert (prompt_dir / "production.txt").read_text(encoding="utf-8") == "v1\n"
    assert (prompt_dir / "v2.yaml").read_bytes() == v2_bytes


def test_rollback_refuses_when_already_oldest(tmp_path: Path):
    prompt_dir = _write_prompt(tmp_path, "diagram_plan", {1: "only $question"}, "v1\n")
    before = (prompt_dir / "production.txt").read_text(encoding="utf-8")

    try:
        rollback_prompt(prompt_dir)
    except ValueError as exc:
        assert "không có version trước" in str(exc)
    else:
        raise AssertionError("phải từ chối khi đang ở version cũ nhất")

    assert (prompt_dir / "production.txt").read_text(encoding="utf-8") == before
    assert (prompt_dir / "v1.yaml").is_file()


def test_rollback_keeps_lint_clean(tmp_path: Path):
    from backend.infra.llm.prompt_lint import lint_prompts_dir

    prompt_dir = _write_prompt(
        tmp_path,
        "answer_compose",
        {1: "ban v1 $question", 2: "ban v2 $question"},
        "v2\n",
    )
    rollback_prompt(prompt_dir)
    assert lint_prompts_dir(tmp_path) == []
