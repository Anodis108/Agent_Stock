"""APScheduler — job định kỳ quét watchlist."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from apscheduler.schedulers.background import BackgroundScheduler

from src.portfolio_watch.shared.logging import get_logger

_logger = get_logger(__name__)


def create_scan_scheduler(
    job: Callable[[], Any],
    *,
    interval_minutes: int = 60,
    job_id: str = "scan_watchlist",
) -> BackgroundScheduler:
    """Tạo scheduler interval; chưa start — caller gọi `.start()`."""
    try:
        minutes = max(int(interval_minutes), 1)
    except (TypeError, ValueError):
        minutes = 60
        _logger.warning(
            "interval_minutes không hợp lệ (%r) → dùng 60", interval_minutes
        )
    scheduler = BackgroundScheduler()

    def _safe_job() -> Any:
        try:
            return job()
        except Exception:  # noqa: BLE001
            _logger.exception("scheduled job %s raised", job_id)
            return None

    scheduler.add_job(
        _safe_job,
        trigger="interval",
        minutes=minutes,
        id=job_id,
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    _logger.info(
        "scan scheduler created job_id=%s interval_minutes=%s",
        job_id,
        minutes,
    )
    return scheduler


def start_scan_scheduler(
    job: Callable[[], Any],
    *,
    interval_minutes: int = 60,
    job_id: str = "scan_watchlist",
) -> BackgroundScheduler:
    scheduler = create_scan_scheduler(
        job, interval_minutes=interval_minutes, job_id=job_id
    )
    scheduler.start()
    _logger.info("scan scheduler started")
    return scheduler


def stop_scan_scheduler(scheduler: BackgroundScheduler | None) -> None:
    if scheduler is None:
        return
    if scheduler.running:
        scheduler.shutdown(wait=False)
        _logger.info("scan scheduler stopped")
