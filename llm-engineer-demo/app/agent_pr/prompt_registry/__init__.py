"""Prompt Registry — git-based, cho `agent_pr` (LLMOps Module III, Phần 4+6).

Trước refactor này, 4 system prompt (`_REWRITE_SYSTEM`, `_SUPERVISOR_SYSTEM`,
`_FINAL_ANSWER_SYSTEM` trong supervisor_agent/nodes.py, `_SENTIMENT_SYSTEM`
trong eval_agent/nodes.py) là hằng số hardcode giữa logic — không version,
không changelog, không tách được người sửa, không A/B test được (đúng 6 hệ
quả liệt kê ở slide "Prompt không được Quản lý").

Registry này tách prompt ra `agent_pr/prompts/<name>/v<N>.yaml` — code chỉ
thấy `get()`/`render()`. Đổi bản đang chạy = sửa `production.txt` (số version)
+ Pull Request, KHÔNG sửa code gọi registry. Rollback = revert PR đó.

Không dùng jinja2 (không phải dependency sẵn có của repo) — biến động
(context, question, ...) dùng `string.Template` (`$var`), đúng slide 17.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from string import Template

import yaml

_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


@dataclass(frozen=True)
class Prompt:
    """Một version cụ thể của 1 prompt + metadata (slide 18)."""

    name: str
    version: int
    model: str
    description: str
    owner: str
    created: str
    changelog: str
    template: str
    status: str = "production"
    eval_score: float | None = None


def _required_vars(template: str) -> set[str]:
    """Tên biến `$var` / `${var}` xuất hiện trong template (string.Template)."""
    matches = Template(template).pattern.finditer(template)
    return {m.group("named") or m.group("braced") for m in matches if m.group("named") or m.group("braced")}


def render(template: str, **kwargs: object) -> str:
    """Render template với biến — báo lỗi rõ ràng khi thiếu biến (slide 17).

    90% lỗi prompt production là "quên truyền biến" hoặc đổi tên biến trong
    template mà quên sửa code gọi — check này chặn ngay lúc render thay vì
    để LLM nhận `$field_bi_thieu` theo nghĩa đen.
    """
    missing = [k for k in _required_vars(template) if k not in kwargs]
    if missing:
        raise ValueError(f"Thiếu biến khi render prompt: {missing}")
    return Template(template).substitute(**kwargs)


class PromptRegistry:
    """Interface tối thiểu (slide 23): code chỉ gọi `get()` / `render()`.

    Chi tiết bên trong (đọc file YAML + production.txt) bị che giấu hoàn
    toàn sau interface này — đổi sang hosted registry sau này (nếu cần) chỉ
    cần thay class này, không đổi chỗ gọi trong nodes.py.
    """

    def __init__(self, root: Path = _PROMPTS_DIR) -> None:
        self._root = root

    def _resolve_version(self, name: str, version: int | str) -> int:
        if isinstance(version, int):
            return version
        if version == "production":
            alias_file = self._root / name / "production.txt"
            try:
                return int(alias_file.read_text(encoding="utf-8").strip())
            except (FileNotFoundError, ValueError) as exc:
                raise ValueError(
                    f"Không đọc được alias 'production' cho prompt '{name}' ({alias_file}): {exc}"
                ) from exc
        if version == "latest":
            versions = sorted(
                int(p.stem[1:])
                for p in (self._root / name).glob("v*.yaml")
                if p.stem[1:].isdigit()
            )
            if not versions:
                raise ValueError(f"Không có version nào cho prompt '{name}'")
            return versions[-1]
        raise ValueError(f"Alias version không hỗ trợ: {version!r}")

    @lru_cache(maxsize=None)
    def _load(self, name: str, version: int) -> Prompt:
        path = self._root / name / f"v{version}.yaml"
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return Prompt(
            name=data["name"],
            version=int(data["version"]),
            model=data.get("model", ""),
            description=data.get("description", ""),
            owner=data.get("owner", ""),
            created=str(data.get("created", "")),
            changelog=data.get("changelog", ""),
            template=data["template"],
            status=data.get("status", "production"),
            eval_score=data.get("eval_score"),
        )

    def get(self, name: str, version: int | str = "production") -> Prompt:
        """`version`: số cụ thể (2) hoặc alias ("production", "latest")."""
        resolved = self._resolve_version(name, version)
        return self._load(name, resolved)

    def render(self, name: str, version: int | str = "production", **variables: object) -> str:
        prompt = self.get(name, version)
        return render(prompt.template, **variables)


@lru_cache
def registry() -> PromptRegistry:
    return PromptRegistry()
