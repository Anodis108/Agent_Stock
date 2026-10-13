#!/usr/bin/env python3
"""Ghi production.txt về version liền trước. Không xoá file vN.yaml."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from backend.infra.llm.prompt_registry import resolve_prompts_dir  # noqa: E402


def list_versions(prompt_dir: Path) -> list[int]:
    versions: list[int] = []
    for path in prompt_dir.glob("v*.yaml"):
        number = path.stem[1:]
        if number.isdigit():
            versions.append(int(number))
    return sorted(versions)


def _alias_version(text: str) -> int | None:
    one_line = text.strip()
    if not one_line or "\n" in one_line:
        return None
    cleaned = one_line[1:] if one_line.lower().startswith("v") else one_line
    if cleaned.isdigit():
        return int(cleaned)
    return None


def current_version(prompt_dir: Path) -> int:
    alias_file = prompt_dir / "production.txt"
    if not alias_file.is_file():
        raise ValueError(f"Thiếu {alias_file}")
    raw = alias_file.read_text(encoding="utf-8")
    pointed = _alias_version(raw)
    if pointed is not None:
        return pointed
    text = raw.strip()
    matched: list[int] = []
    for version in list_versions(prompt_dir):
        data = yaml.safe_load((prompt_dir / f"v{version}.yaml").read_text(encoding="utf-8"))
        template = ""
        if isinstance(data, dict):
            template = str(data.get("template") or "")
        if template.strip() == text:
            matched.append(version)
    if not matched:
        raise ValueError(f"Không xác định được version hiện tại của {prompt_dir.name}")
    return matched[-1]


def previous_version(prompt_dir: Path) -> int:
    current = current_version(prompt_dir)
    older = [version for version in list_versions(prompt_dir) if version < current]
    if not older:
        raise ValueError(f"{prompt_dir.name} đang ở v{current}, không có version trước")
    return older[-1]


def rollback_prompt(prompt_dir: Path, *, dry_run: bool = False) -> int:
    """Ghi production.txt thành vN của version liền trước. Giữ mọi file vN.yaml."""
    target = previous_version(prompt_dir)
    if not dry_run:
        (prompt_dir / "production.txt").write_text(f"v{target}\n", encoding="utf-8")
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Rollback alias production.txt về version trước.")
    parser.add_argument("name", help="Tên thư mục prompt, ví dụ answer_compose")
    parser.add_argument("--root", default=str(resolve_prompts_dir()), help="Thư mục resources/prompts")
    parser.add_argument("--dry-run", action="store_true", help="Chỉ in version đích, không ghi file")
    args = parser.parse_args(argv)
    prompt_dir = Path(args.root) / args.name
    if not prompt_dir.is_dir():
        print(f"Không thấy prompt {prompt_dir}", file=sys.stderr)
        return 1
    try:
        target = rollback_prompt(prompt_dir, dry_run=args.dry_run)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    action = "sẽ ghi" if args.dry_run else "đã ghi"
    print(f"{action} {prompt_dir / 'production.txt'} -> v{target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
