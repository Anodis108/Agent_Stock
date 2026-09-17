"""Prompt Registry git-based — Lesson16 / pattern llm-engineer-demo agent_pr.

Đọc `prompts/<name>/vN.yaml` + alias `production.txt`. Code chỉ gọi
`get()` / `render()` — đổi bản production = sửa file, không sửa caller.
Template engine: `string.Template` (`$var`), không Jinja2.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from string import Template

import yaml


def resolve_prompts_dir() -> Path:
    """Tìm `prompts/` — local editable, Docker `/app/prompts`, hoặc cwd."""
    here = Path(__file__).resolve()
    candidates = (
        here.parents[4] / "prompts",  # .../project/prompts (editable)
        Path("/app/prompts"),
        Path.cwd() / "prompts",
    )
    for cand in candidates:
        if cand.is_dir() and (cand / "event_classification" / "v1.yaml").is_file():
            return cand
    return candidates[0]


@dataclass(frozen=True)
class Prompt:
    """Một version cụ thể của 1 prompt + metadata."""

    name: str
    version: int
    model: str
    description: str
    owner: str
    created: str
    changelog: str
    template: str
    eval_score: float | None = None


def _required_vars(template: str) -> set[str]:
    """Tên biến `$var` / `${var}` trong template (string.Template)."""
    names: set[str] = set()
    for match in Template(template).pattern.finditer(template):
        name = match.group("named") or match.group("braced")
        if name:
            names.add(name)
    return names


def _render_template(template: str, **kwargs: object) -> str:
    """Render — raise rõ khi thiếu biến bắt buộc (không silent / safe_substitute)."""
    missing = sorted(k for k in _required_vars(template) if k not in kwargs)
    if missing:
        raise ValueError(f"Thiếu biến khi render prompt: {missing}")
    return Template(template).substitute(
        {k: "" if v is None else str(v) for k, v in kwargs.items()}
    )


class PromptRegistry:
    """Interface tối thiểu: `get(name, version)` / `render(name, version, **vars)`."""

    def __init__(self, root: Path | None = None) -> None:
        self._root = Path(root) if root is not None else resolve_prompts_dir()

    def _resolve_version(self, name: str, version: int | str) -> int:
        if isinstance(version, int):
            return version
        text = str(version).strip()
        if text.isdigit():
            return int(text)
        if text == "production":
            alias_file = self._root / name / "production.txt"
            try:
                return int(alias_file.read_text(encoding="utf-8").strip())
            except (FileNotFoundError, ValueError) as exc:
                raise ValueError(
                    f"Không đọc được alias 'production' cho prompt '{name}' "
                    f"({alias_file}): {exc}"
                ) from exc
        if text == "latest":
            versions = sorted(
                int(p.stem[1:])
                for p in (self._root / name).glob("v*.yaml")
                if p.stem.startswith("v") and p.stem[1:].isdigit()
            )
            if not versions:
                raise ValueError(f"Không có version nào cho prompt '{name}'")
            return versions[-1]
        raise ValueError(f"Alias version không hỗ trợ: {version!r}")

    def _load(self, name: str, version: int) -> Prompt:
        path = self._root / name / f"v{version}.yaml"
        if not path.is_file():
            raise FileNotFoundError(
                f"Không tìm thấy prompt '{name}' version {version} tại {path}"
            )
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or "template" not in data:
            raise ValueError(f"Prompt YAML không hợp lệ: {path}")
        return Prompt(
            name=str(data.get("name", name)),
            version=int(data["version"]),
            model=str(data.get("model", "")),
            description=str(data.get("description", "")),
            owner=str(data.get("owner", "")),
            created=str(data.get("created", "")),
            changelog=str(data.get("changelog", "")),
            template=str(data["template"]),
            eval_score=data.get("eval_score"),
        )

    def get(self, name: str, version: int | str = "production") -> Prompt:
        """`version`: số cụ thể hoặc alias `"production"` / `"latest"`."""
        resolved = self._resolve_version(name, version)
        return self._load(name, resolved)

    def render(
        self, name: str, version: int | str = "production", **variables: object
    ) -> str:
        prompt = self.get(name, version)
        return _render_template(prompt.template, **variables)


@lru_cache
def registry() -> PromptRegistry:
    """Singleton mặc định — trỏ `prompts/` ở project root / Docker."""
    return PromptRegistry()
