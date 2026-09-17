"""HITL Gate 1 / Gate 2 — approve hoặc reject bản ghi chờ duyệt."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.portfolio_watch.domain.entities import (
    AlertStatus,
    FinalAlert,
    WatchlistItem,
)
from src.portfolio_watch.domain.ports import MemoryStore, Notifier, WatchlistStore
from src.portfolio_watch.shared.logging import get_logger

_logger = get_logger(__name__)
DEFAULT_THRESHOLD_PCT = 3.0
_EVENT_LIMIT = 500


@dataclass(slots=True)
class ReviewResult:
    ok: bool
    action: str  # approved | rejected
    approval_id: str
    gate: str | None = None
    error: str | None = None
    alert: FinalAlert | None = None
    watchlist_updates: list[WatchlistItem] | None = None


def _approval_id_of(event: dict[str, Any]) -> str | None:
    if event.get("gate") == "gate1":
        return event.get("alert_id") or (event.get("alert") or {}).get("id")
    if event.get("gate") == "gate2":
        return event.get("proposal_id")
    return event.get("alert_id") or event.get("proposal_id")


def _is_resolution(event: dict[str, Any], approval_id: str) -> bool:
    if event.get("kind") not in ("resolution", "approved", "rejected"):
        return False
    # Khớp approval_id hoặc alias Gate1/Gate2 để không duyệt lại khi event
    # chỉ ghi alert_id / proposal_id.
    if event.get("approval_id") == approval_id:
        return True
    if event.get("alert_id") == approval_id:
        return True
    if event.get("proposal_id") == approval_id:
        return True
    return False


def list_pending_approvals(
    memory_store: MemoryStore,
    user_id: str = "default",
    *,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Danh sách pending chưa có resolution (Gate 1 + Gate 2)."""
    events = memory_store.list_alert_events(user_id, limit=_EVENT_LIMIT)
    resolved: set[str] = set()
    for e in events:
        if e.get("kind") in ("resolution", "approved", "rejected"):
            for key in ("approval_id", "alert_id", "proposal_id"):
                val = e.get(key)
                if val:
                    resolved.add(str(val))
        # Gate 1 đã gửi: kind=sent với cùng alert_id
        if e.get("kind") == "sent" and e.get("alert_id"):
            resolved.add(str(e["alert_id"]))

    pending: list[dict[str, Any]] = []
    for e in events:
        if e.get("kind") != "pending_approval":
            continue
        if e.get("status") and e.get("status") != AlertStatus.PENDING_APPROVAL.value:
            continue
        aid = _approval_id_of(e)
        if not aid or str(aid) in resolved:
            continue
        pending.append({**e, "approval_id": str(aid)})
    return pending[-max(limit, 1) :]


def _find_pending(
    memory_store: MemoryStore, user_id: str, approval_id: str
) -> tuple[dict[str, Any] | None, str | None]:
    aid = (approval_id or "").strip()
    if not aid:
        return None, "approval_id rỗng"

    events = memory_store.list_alert_events(user_id, limit=_EVENT_LIMIT)
    pending: dict[str, Any] | None = None
    for e in events:
        if e.get("kind") != "pending_approval":
            continue
        if _approval_id_of(e) == aid:
            pending = e

    if pending is None:
        return None, "không tìm thấy bản ghi chờ duyệt"

    for e in events:
        if _is_resolution(e, aid):
            return pending, "bản ghi đã xử lý rồi"
        if e.get("kind") == "sent" and e.get("alert_id") == aid:
            return pending, "bản ghi đã xử lý rồi"

    return pending, None


def _append_resolution(
    memory_store: MemoryStore,
    user_id: str,
    *,
    approval_id: str,
    gate: str,
    action: str,
    extra: dict[str, Any] | None = None,
) -> None:
    event: dict[str, Any] = {
        "kind": "resolution",
        "approval_id": approval_id,
        "gate": gate,
        "action": action,
        "status": (
            AlertStatus.SENT.value
            if action == "approved" and gate == "gate1"
            else (
                AlertStatus.REJECTED.value
                if action == "rejected"
                else "applied"
            )
        ),
    }
    if extra:
        event.update(extra)
    memory_store.append_alert_event(user_id, event)


def approve_pending(
    approval_id: str,
    *,
    memory_store: MemoryStore,
    notifier: Notifier,
    watchlist_store: WatchlistStore,
    user_id: str = "default",
) -> ReviewResult:
    pending, err = _find_pending(memory_store, user_id, approval_id)
    if err or pending is None:
        return ReviewResult(
            ok=False,
            action="approved",
            approval_id=approval_id or "",
            gate=pending.get("gate") if pending else None,
            error=err or "không tìm thấy bản ghi chờ duyệt",
        )

    gate = str(pending.get("gate") or "")
    aid = str(_approval_id_of(pending) or approval_id)

    if gate == "gate1":
        raw = pending.get("alert") or {}
        try:
            alert = FinalAlert.model_validate(raw)
        except Exception as exc:  # noqa: BLE001
            return ReviewResult(
                ok=False,
                action="approved",
                approval_id=aid,
                gate=gate,
                error=f"alert không hợp lệ: {exc}",
            )
        alert.metadata = {**alert.metadata, "user_id": user_id}
        if alert.status == AlertStatus.REJECTED:
            return ReviewResult(
                ok=False,
                action="approved",
                approval_id=aid,
                gate=gate,
                error="alert đã reject, không gửi",
                alert=alert,
            )
        try:
            notifier.send(alert)
        except Exception as exc:  # noqa: BLE001
            return ReviewResult(
                ok=False,
                action="approved",
                approval_id=aid,
                gate=gate,
                error=f"gửi cảnh báo lỗi: {exc}",
                alert=alert,
            )
        # AC: Approve Gate 1 → trạng thái "đã gửi"
        if alert.status != AlertStatus.SENT:
            alert.status = AlertStatus.SENT
        _append_resolution(
            memory_store,
            user_id,
            approval_id=aid,
            gate=gate,
            action="approved",
            extra={"alert_id": aid, "symbol": alert.symbol},
        )
        _logger.info("Gate1 approved → sent id=%s symbol=%s", aid, alert.symbol)
        return ReviewResult(
            ok=True,
            action="approved",
            approval_id=aid,
            gate=gate,
            alert=alert,
        )

    if gate == "gate2":
        symbol = str(pending.get("symbol") or "").strip().upper()
        if not symbol:
            return ReviewResult(
                ok=False,
                action="approved",
                approval_id=aid,
                gate=gate,
                error="gate2 thiếu symbol",
            )
        updates: list[WatchlistItem] = []
        proposed_thr = pending.get("proposed_threshold_pct")
        existing = watchlist_store.get(user_id, symbol)
        if proposed_thr is not None:
            thr = float(proposed_thr)
        elif existing is not None:
            thr = float(existing.threshold_pct)
        else:
            thr = DEFAULT_THRESHOLD_PCT
        if thr < 0:
            return ReviewResult(
                ok=False,
                action="approved",
                approval_id=aid,
                gate=gate,
                error="ngưỡng đề xuất không hợp lệ",
            )
        item = WatchlistItem(symbol=symbol, threshold_pct=thr, user_id=user_id)
        watchlist_store.upsert(item)
        updates.append(item)

        for rel in pending.get("proposed_related_symbols") or []:
            rel_sym = str(rel).strip().upper()
            if not rel_sym or rel_sym == symbol:
                continue
            if watchlist_store.get(user_id, rel_sym) is None:
                rel_item = WatchlistItem(
                    symbol=rel_sym, threshold_pct=thr, user_id=user_id
                )
                watchlist_store.upsert(rel_item)
                updates.append(rel_item)

        _append_resolution(
            memory_store,
            user_id,
            approval_id=aid,
            gate=gate,
            action="approved",
            extra={
                "symbol": symbol,
                "proposed_threshold_pct": proposed_thr,
                "applied_threshold_pct": thr,
            },
        )
        _logger.info(
            "Gate2 approved id=%s symbol=%s threshold=%s", aid, symbol, thr
        )
        return ReviewResult(
            ok=True,
            action="approved",
            approval_id=aid,
            gate=gate,
            watchlist_updates=updates,
        )

    return ReviewResult(
        ok=False,
        action="approved",
        approval_id=aid,
        gate=gate or None,
        error=f"gate không hỗ trợ: {gate}",
    )


def reject_pending(
    approval_id: str,
    reason: str,
    *,
    memory_store: MemoryStore,
    watchlist_store: WatchlistStore | None = None,
    user_id: str = "default",
) -> ReviewResult:
    pending, err = _find_pending(memory_store, user_id, approval_id)
    if err or pending is None:
        return ReviewResult(
            ok=False,
            action="rejected",
            approval_id=approval_id or "",
            gate=pending.get("gate") if pending else None,
            error=err or "không tìm thấy bản ghi chờ duyệt",
        )

    gate = str(pending.get("gate") or "")
    aid = str(_approval_id_of(pending) or approval_id)
    why = (reason or "").strip()
    if not why:
        return ReviewResult(
            ok=False,
            action="rejected",
            approval_id=aid,
            gate=gate,
            error="lý do reject rỗng",
        )

    # Snapshot watchlist Gate 2 trước reject để đảm bảo không đổi
    before: dict[str, float] = {}
    symbol = str(pending.get("symbol") or "").strip().upper()
    if gate == "gate2" and watchlist_store is not None and symbol:
        cur = watchlist_store.get(user_id, symbol)
        if cur is not None:
            before[symbol] = cur.threshold_pct
        for rel in pending.get("proposed_related_symbols") or []:
            rel_sym = str(rel).strip().upper()
            if not rel_sym:
                continue
            rel_item = watchlist_store.get(user_id, rel_sym)
            if rel_item is not None:
                before[rel_sym] = rel_item.threshold_pct

    memory_store.record_rejection(
        user_id,
        gate=gate or "unknown",
        reason=why,
        context={
            "approval_id": aid,
            "symbol": pending.get("symbol"),
            "pending": {
                k: pending.get(k)
                for k in (
                    "alert_id",
                    "proposal_id",
                    "proposed_threshold_pct",
                    "proposed_related_symbols",
                )
            },
        },
    )

    alert: FinalAlert | None = None
    if gate == "gate1" and pending.get("alert"):
        try:
            alert = FinalAlert.model_validate(pending["alert"])
            alert.status = AlertStatus.REJECTED
            alert.reject_reason = why
        except Exception:  # noqa: BLE001
            alert = None

    _append_resolution(
        memory_store,
        user_id,
        approval_id=aid,
        gate=gate,
        action="rejected",
        extra={"symbol": pending.get("symbol"), "reason": why},
    )

    # Gate 2: không được đụng watchlist (kể cả mã liên quan)
    if gate == "gate2" and watchlist_store is not None and before:
        for sym_key, thr in before.items():
            cur = watchlist_store.get(user_id, sym_key)
            if cur is not None and cur.threshold_pct != thr:
                watchlist_store.upsert(
                    WatchlistItem(
                        symbol=sym_key,
                        threshold_pct=thr,
                        user_id=user_id,
                    )
                )
            elif cur is None:
                # Không tự thêm mã khi reject
                pass

    _logger.info("Gate %s rejected id=%s reason=%s", gate, aid, why)
    return ReviewResult(
        ok=True,
        action="rejected",
        approval_id=aid,
        gate=gate,
        alert=alert,
    )
