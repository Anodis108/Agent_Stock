from __future__ import annotations

import logging

import pytest

from src.portfolio_watch.domain.entities import (
    AlertStatus,
    FinalAlert,
    Severity,
    SeverityLevel,
)
from src.portfolio_watch.infra.notify.console_notifier import ConsoleNotifier
from src.portfolio_watch.infra.storage.memory_store import SqliteMemoryStore


def _sample_alert(**overrides) -> FinalAlert:
    data = {
        "id": "a1",
        "symbol": "FPT",
        "title": "FPT biến động",
        "body": "Giá tăng 5% kèm tin KQKD.",
        "severity": Severity(
            level=SeverityLevel.HIGH,
            confidence=0.9,
            reasoning="biến động lớn",
            evidence=["change_pct=5"],
        ),
        "status": AlertStatus.DRAFT,
        "metadata": {},
    }
    data.update(overrides)
    return FinalAlert(**data)


def test_console_notifier_logs_and_persists(tmp_path, caplog):
    mem = SqliteMemoryStore(str(tmp_path / "notify.db"))
    notifier = ConsoleNotifier(mem)

    with caplog.at_level(
        logging.INFO, logger="src.portfolio_watch.infra.notify.console_notifier"
    ):
        alert = _sample_alert()
        notifier.send(alert)

    assert alert.status == AlertStatus.SENT
    assert any(
        "ALERT sent" in r.message and "FPT" in r.message for r in caplog.records
    )

    events = mem.list_alert_events("default")
    assert len(events) == 1
    assert events[0]["kind"] == "sent"
    assert events[0]["symbol"] == "FPT"
    assert events[0]["status"] == "sent"
    assert events[0]["title"] == "FPT biến động"


def test_console_notifier_uses_metadata_user_id(tmp_path):
    mem = SqliteMemoryStore(str(tmp_path / "notify2.db"))
    notifier = ConsoleNotifier(mem, user_id="default")
    notifier.send(_sample_alert(metadata={"user_id": "u42"}))

    assert mem.list_alert_events("default") == []
    events = mem.list_alert_events("u42")
    assert len(events) == 1
    assert events[0]["symbol"] == "FPT"


def test_console_notifier_skips_rejected(tmp_path, caplog):
    mem = SqliteMemoryStore(str(tmp_path / "notify3.db"))
    notifier = ConsoleNotifier(mem)
    alert = _sample_alert(
        status=AlertStatus.REJECTED, reject_reason="spam"
    )

    with caplog.at_level(
        logging.WARNING, logger="src.portfolio_watch.infra.notify.console_notifier"
    ):
        notifier.send(alert)

    assert alert.status == AlertStatus.REJECTED
    assert mem.list_alert_events("default") == []
    assert any("skip rejected" in r.message for r in caplog.records)


def test_console_notifier_db_fail_keeps_status():
    class BoomMem:
        def append_alert_event(self, user_id, event):
            raise RuntimeError("db down")

    alert = _sample_alert(status=AlertStatus.DRAFT)
    with pytest.raises(RuntimeError, match="db down"):
        ConsoleNotifier(BoomMem()).send(alert)
    assert alert.status == AlertStatus.DRAFT
