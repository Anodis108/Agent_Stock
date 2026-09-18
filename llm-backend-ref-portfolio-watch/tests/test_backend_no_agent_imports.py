"""Phase 3b — Backend không import domain.agents / graph; chỉ HTTP tới AI.

Khớp product-spec AC7 và test-plan «Backend không import agents».
"""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"

# Cấm import agent/graph domain vào process Backend
_FORBIDDEN_SUBSTRINGS = (
    "domain.agents",
    "portfolio_watch.domain.agents",
    "portfolio_watch.application",
    "langgraph",
    "langchain",
)


def _iter_backend_py() -> list[Path]:
    return sorted(BACKEND_DIR.rglob("*.py"))


def _module_refs(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    refs: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            refs.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                refs.append(node.module)
    return refs


def test_backend_python_files_forbid_agent_domain_imports():
    offenders: list[str] = []
    for path in _iter_backend_py():
        for mod in _module_refs(path):
            if any(f in mod for f in _FORBIDDEN_SUBSTRINGS):
                offenders.append(f"{path.relative_to(ROOT)}: import {mod}")
    assert offenders == [], "Backend được phép chỉ HTTP client, không import agents:\n" + "\n".join(
        offenders
    )


def test_backend_does_not_import_src_portfolio_watch_package():
    """Tách process: backend/ không phụ thuộc package AI domain."""
    offenders: list[str] = []
    for path in _iter_backend_py():
        for mod in _module_refs(path):
            if mod == "src" or mod.startswith("src.portfolio_watch"):
                offenders.append(f"{path.relative_to(ROOT)}: import {mod}")
    assert offenders == [], offenders


def test_ai_client_is_stdlib_http_only():
    path = BACKEND_DIR / "ai_client.py"
    text = path.read_text(encoding="utf-8")
    refs = _module_refs(path)
    assert "urllib.request" in refs or "urllib.request" in text
    assert not any("domain.agents" in m for m in refs)
    assert not any(m.startswith("src.portfolio_watch") for m in refs)
    # Body gọi AI path nội bộ, không gọi application layer
    body = "\n".join(
        ln for ln in text.splitlines() if not ln.strip().startswith("#") and '"""' not in ln
    )
    assert "answer_question" not in body and "scan_symbol" not in body
    assert "/v1/chat" in text and "/v1/scan" in text


def test_backend_readme_states_http_only_boundary():
    readme = (BACKEND_DIR / "README.md").read_text(encoding="utf-8")
    assert "domain.agents" in readme
    assert "HTTP" in readme or "AI_BASE_URL" in readme
