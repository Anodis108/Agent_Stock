"""Notifier MVP — in ra console/log và ghi MemoryStore."""

from __future__ import annotations

from src.portfolio_watch.domain.entities import AlertStatus, FinalAlert
from src.portfolio_watch.domain.ports import MemoryStore
from src.portfolio_watch.shared.logging import get_logger

_logger = get_logger(__name__)


class ConsoleNotifier:
    """Gửi cảnh báo: log console + append_alert_event (status sent)."""

    def __init__(self, memory: MemoryStore, user_id: str = "default"):
        self._memory = memory
        self._user_id = user_id

    def send(self, alert: FinalAlert) -> None:
        # test-plan: reject → không gửi
        if alert.status == AlertStatus.REJECTED:
            _logger.warning(
                "ALERT skip rejected symbol=%s id=%s",
                alert.symbol,
                alert.id,
            )
            return

        user_id = str(alert.metadata.get("user_id") or self._user_id)
        event = {
            "kind": "sent",
            "alert_id": alert.id,
            "symbol": alert.symbol,
            "title": alert.title,
            "body": alert.body,
            "status": AlertStatus.SENT.value,
            "severity": alert.severity.model_dump(mode="json"),
            "metadata": dict(alert.metadata),
        }
        # Ghi DB trước — chỉ đánh dấu SENT khi persist thành công
        self._memory.append_alert_event(user_id, event)
        alert.status = AlertStatus.SENT
        _logger.info(
            "ALERT sent symbol=%s title=%s severity=%s confidence=%.2f | %s",
            alert.symbol,
            alert.title,
            alert.severity.level.value,
            alert.severity.confidence,
            alert.body,
        )
