"""Thư mục ảnh biểu đồ và định dạng Matplotlib chuẩn cho AI Backend."""

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


def apply_chart_style(dark_mode: bool = True) -> None:
    """Thiết lập cấu hình Matplotlib rcParams chuẩn thẩm mỹ tài chính (Dark/Light)."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        if dark_mode:
            plt.style.use("dark_background")
            plt.rcParams.update({
                "figure.facecolor": "#131722",
                "axes.facecolor": "#1e222d",
                "axes.edgecolor": "#2a2e39",
                "axes.labelcolor": "#d1d4dc",
                "text.color": "#d1d4dc",
                "xtick.color": "#787b86",
                "ytick.color": "#787b86",
                "grid.color": "#2a2e39",
                "grid.alpha": 0.5,
                "grid.linestyle": "--",
                "figure.dpi": 150,
                "font.sans-serif": ["Segoe UI", "DejaVu Sans", "Helvetica", "Arial"],
            })
        else:
            plt.style.use("default")
            plt.rcParams.update({
                "figure.facecolor": "#ffffff",
                "axes.facecolor": "#f8f9fa",
                "axes.edgecolor": "#dfe2e5",
                "axes.labelcolor": "#24292e",
                "text.color": "#24292e",
                "xtick.color": "#586069",
                "ytick.color": "#586069",
                "grid.color": "#e1e4e8",
                "grid.alpha": 0.7,
                "grid.linestyle": ":",
                "figure.dpi": 150,
                "font.sans-serif": ["Segoe UI", "DejaVu Sans", "Helvetica", "Arial"],
            })
    except ImportError:
        pass
