"""Eval history — M3-B2 Phase 6: lưu lịch sử chạy eval + đo noise (σ).

Mỗi lần chạy (khi `--save-history`) lưu JSON vào:
    specs/eval/history/<timestamp>_<git_sha>.json
"""

from __future__ import annotations

import json
import statistics
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from backend.eval.run import _find_project_root


def resolve_history_dir(root: Path | None = None) -> Path:
    base = root or _find_project_root()
    return base / "specs" / "eval" / "history"


def get_git_sha() -> str:
    """Short git SHA — 'unknown' nếu không trong repo."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            cwd=str(_find_project_root()),
        )
        sha = (out.stdout or "").strip()
        return sha or "unknown"
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def build_history_filename(
    sha: str,
    *,
    ts: datetime | None = None,
) -> str:
    when = ts or datetime.now(timezone.utc)
    stamp = when.strftime("%Y%m%dT%H%M%SZ")
    safe_sha = "".join(c for c in sha if c.isalnum()) or "unknown"
    return f"{stamp}_{safe_sha}.json"


def save_eval_history(
    payload: dict,
    *,
    history_dir: Path | None = None,
    sha: str | None = None,
    extra_meta: dict | None = None,
) -> Path:
    """Lưu report JSON vào specs/eval/history/."""
    directory = history_dir or resolve_history_dir()
    directory.mkdir(parents=True, exist_ok=True)
    commit = sha or get_git_sha()
    path = directory / build_history_filename(commit)
    record = {
        "saved_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "git_sha": commit,
        **(extra_meta or {}),
        "report": payload,
    }
    path.write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def load_history_reports(history_dir: Path | None = None) -> list[dict]:
    """Đọc mọi file history — trả về list record (metadata + report)."""
    directory = history_dir or resolve_history_dir()
    if not directory.is_dir():
        return []
    records: list[dict] = []
    for path in sorted(directory.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if isinstance(data, dict):
            data["_path"] = str(path)
            records.append(data)
    return records


def extract_overall_rate(record: dict) -> float | None:
    """Lấy overall rate từ history record."""
    report = record.get("report")
    if isinstance(report, dict) and "rate" in report:
        return float(report["rate"])
    if "rate" in record:
        return float(record["rate"])
    return None


def compute_noise_stats(rates: list[float]) -> dict:
    """Tính mean, σ và gợi ý drop_tolerance (σ + buffer 0.01)."""
    if not rates:
        return {
            "count": 0,
            "mean": None,
            "stdev": None,
            "recommended_drop_tolerance": 0.03,
        }
    if len(rates) == 1:
        return {
            "count": 1,
            "mean": rates[0],
            "stdev": 0.0,
            "recommended_drop_tolerance": 0.03,
        }
    stdev = statistics.stdev(rates)
    mean = statistics.mean(rates)
    buffer = 0.01
    recommended = max(0.03, round(stdev + buffer, 4))
    return {
        "count": len(rates),
        "mean": mean,
        "stdev": stdev,
        "recommended_drop_tolerance": recommended,
    }


def calibrate_tolerance_from_history(
    history_dir: Path | None = None,
    *,
    min_runs: int = 3,
) -> dict:
    """Calibrate drop_tolerance từ ≥ min_runs history entries cùng commit (hoặc tất cả)."""
    records = load_history_reports(history_dir)
    rates = [r for rec in records if (r := extract_overall_rate(rec)) is not None]
    stats = compute_noise_stats(rates)
    stats["min_runs_required"] = min_runs
    stats["sufficient_data"] = len(rates) >= min_runs
    if stats["sufficient_data"]:
        stats["note"] = (
            f"Gợi ý drop_tolerance = {stats['recommended_drop_tolerance']} "
            f"(σ={stats['stdev']:.4f} + buffer 0.01)"
        )
    else:
        stats["note"] = (
            f"Cần ≥ {min_runs} runs để calibrate — hiện có {len(rates)}; "
            "giữ mặc định 0.03"
        )
    return stats
