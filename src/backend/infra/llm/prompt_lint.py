"""Prompt lint — M3-B1 Phase 3: CI-ready validation cho `resources/prompts/`.

Kiểm tra:
- metadata bắt buộc (name, version, model, owner, changelog, template)
- `name` khớp thư mục; `version` khớp tên file vN.yaml
- biến `$var` trong template khớp khai báo `variables:` (nếu có)
- các version cùng prompt có cùng tập biến template
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

from backend.infra.llm.prompt_registry import _required_vars, resolve_prompts_dir

REQUIRED_META = ("name", "version", "model", "owner", "changelog", "template")


@dataclass(frozen=True)
class LintIssue:
    path: str
    message: str

    def __str__(self) -> str:
        return f"{self.path}: {self.message}"


def _load_yaml(path: Path) -> dict | None:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        return {"__parse_error__": str(exc)}
    return data if isinstance(data, dict) else {}


def lint_prompt_file(path: Path, *, prompt_name: str) -> list[LintIssue]:
    """Lint một file vN.yaml."""
    rel = str(path)
    issues: list[LintIssue] = []
    data = _load_yaml(path)
    if data is None:
        return [LintIssue(rel, "YAML không phải object")]
    if "__parse_error__" in data:
        return [LintIssue(rel, f"YAML parse error: {data['__parse_error__']}")]

    for field in REQUIRED_META:
        value = data.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            issues.append(LintIssue(rel, f"Thiếu hoặc rỗng metadata '{field}'"))

    file_version = path.stem[1:] if path.stem.startswith("v") else None
    if file_version and file_version.isdigit():
        yaml_version = data.get("version")
        if yaml_version is not None and int(yaml_version) != int(file_version):
            issues.append(
                LintIssue(
                    rel,
                    f"version trong YAML ({yaml_version}) != tên file (v{file_version})",
                )
            )

    yaml_name = str(data.get("name", "")).strip()
    if yaml_name and yaml_name != prompt_name:
        issues.append(
            LintIssue(rel, f"name '{yaml_name}' != thư mục prompt '{prompt_name}'")
        )

    template = str(data.get("template", ""))
    template_vars = _required_vars(template)

    declared = data.get("variables")
    if declared is not None:
        if not isinstance(declared, list):
            issues.append(LintIssue(rel, "Trường 'variables' phải là list"))
        else:
            declared_set = {str(v).strip() for v in declared if str(v).strip()}
            if declared_set != template_vars:
                issues.append(
                    LintIssue(
                        rel,
                        f"variables khai báo {sorted(declared_set)} "
                        f"!= biến template {sorted(template_vars)}",
                    )
                )

    return issues


def lint_prompts_dir(root: Path) -> list[LintIssue]:
    """Lint toàn bộ thư mục prompts/."""
    issues: list[LintIssue] = []
    if not root.is_dir():
        return [LintIssue(str(root), "Thư mục prompts không tồn tại")]

    for prompt_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        prompt_name = prompt_dir.name
        version_files = sorted(prompt_dir.glob("v*.yaml"))
        if not version_files:
            issues.append(
                LintIssue(str(prompt_dir), "Không có file v*.yaml")
            )
            continue

        if not (prompt_dir / "production.txt").is_file():
            issues.append(
                LintIssue(str(prompt_dir), "Thiếu production.txt")
            )

        vars_by_version: dict[int, set[str]] = {}
        for vf in version_files:
            file_issues = lint_prompt_file(vf, prompt_name=prompt_name)
            issues.extend(file_issues)
            data = _load_yaml(vf)
            if isinstance(data, dict) and "template" in data:
                ver = int(data.get("version", vf.stem[1:]))
                vars_by_version[ver] = _required_vars(str(data["template"]))

        if len(vars_by_version) > 1:
            ref_ver = min(vars_by_version)
            ref_vars = vars_by_version[ref_ver]
            for ver, vars_set in vars_by_version.items():
                if ver != ref_ver and vars_set != ref_vars:
                    issues.append(
                        LintIssue(
                            str(prompt_dir),
                            f"v{ver} biến template {sorted(vars_set)} "
                            f"!= v{ref_ver} {sorted(ref_vars)}",
                        )
                    )

    return issues


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Lint prompt registry YAML files.")
    parser.add_argument(
        "prompts_dir",
        nargs="?",
        default=str(resolve_prompts_dir()),
        help="Đường dẫn tới resources/prompts/ (mặc định: auto-detect)",
    )
    args = parser.parse_args(argv)
    root = Path(args.prompts_dir)
    issues = lint_prompts_dir(root)
    if issues:
        for issue in issues:
            print(issue, file=sys.stderr)
        print(f"\n{len(issues)} lint error(s)", file=sys.stderr)
        return 1
    print(f"OK: {root} — all prompts passed lint")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
