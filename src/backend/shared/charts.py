"""Thư mục ảnh biểu đồ. Web và ChartAgent dùng chung, không kéo Matplotlib."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from uuid import uuid4


def _is_dir_writable(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        test_file = path / f".write_test_{uuid4().hex[:6]}"
        test_file.touch()
        test_file.unlink()
        return True
    except (OSError, PermissionError):
        return False


def get_charts_dir() -> Path:
    """Đường dẫn thư mục lưu ảnh biểu đồ (máy local và Docker)."""
    env_dir = os.environ.get("CHARTS_DIR")
    if env_dir:
        path = Path(env_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path

    root = None
    p = Path(__file__).resolve().parent
    for _ in range(6):
        if (p / "pyproject.toml").is_file():
            root = p
            break
        p = p.parent
    if root is None:
        root = Path(__file__).resolve().parents[3]
    candidates: list[Path] = []
    if Path("/app/data").is_dir():
        candidates.append(Path("/app/data/charts"))
    candidates.append(root / "resources" / "data" / "charts")
    candidates.append(root / "data" / "charts")

    for cand in candidates:
        if _is_dir_writable(cand):
            return cand

    fallback = Path(tempfile.gettempdir()) / "portfolio_watch_charts"
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback
