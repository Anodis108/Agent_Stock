"""HITL — hàng đợi duyệt hành động scan (Web Backend).

Giống llm-engineer-demo: graph scan (AI Backend) DỪNG trước scan_tools (interrupt_before) và ghi event
`pending_approval` {approval_id, thread_id, gate=tên tool, args} vào memory_store. Web Backend chỉ liệt kê
và gọi `resume(thread_id, approve, reason)` sang AI Backend — tool `update_watchlist` chạy
TRONG graph, Web Backend không tự gửi cảnh báo hay sửa watchlist.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from common.domain.ports import MemoryStore
from common.logging.logger import get_logger

_logger = get_logger("web_backend.application.review_approval")
_EVENT_LIMIT = 500

# resume(thread_id, approve, reason, user_id) → response /v1/scan/resume (RemoteAiClient.scan_resume)
ResumeFn = Callable[[str, bool, str, str], dict[str, Any]]


@dataclass(slots=True)
class ReviewResult:
    ok: bool
    action: str  # approved | rejected
    approval_id: str
    gate: str | None = None  # tên tool: update_watchlist
    error: str | None = None
    next_status: str | None = None  # done | pending_approval (graph dừng ở hành động kế)


def list_pending_approvals(
    memory_store: MemoryStore,
    user_id: str = "default",
    *,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Hành động scan đang chờ duyệt (có thread_id để resume) và chưa có resolution."""
    if memory_store is None or not hasattr(memory_store, "list_alert_events"):
        return []
    events = memory_store.list_alert_events(user_id, limit=_EVENT_LIMIT)
    resolved = {str(e["approval_id"]) for e in events if e.get("kind") == "resolution" and e.get("approval_id")}
    pending = [
        {**e, "id": e["approval_id"]}
        for e in events
        if e.get("kind") == "pending_approval" and e.get("thread_id") and str(e.get("approval_id")) not in resolved
    ]
    return pending[-max(limit, 1) :]


def _review(
    approval_id: str,
    approve: bool,
    reason: str,
    *,
    memory_store: MemoryStore,
    resume: ResumeFn,
    user_id: str,
) -> ReviewResult:
    """Tìm pending theo approval_id → resume graph trên AI Backend → ghi resolution."""
    action = "approved" if approve else "rejected"
    aid = (approval_id or "").strip()
    pending = next((e for e in list_pending_approvals(memory_store, user_id, limit=_EVENT_LIMIT) if e["id"] == aid), None)
    if pending is None:
        return ReviewResult(ok=False, action=action, approval_id=aid, error="không tìm thấy bản ghi chờ duyệt")

    gate = pending.get("gate")
    try:
        out = resume(pending["thread_id"], approve, reason, user_id)
    except Exception as exc:  # noqa: BLE001
        return ReviewResult(ok=False, action=action, approval_id=aid, gate=gate, error=f"resume lỗi: {exc}")

    if not approve and hasattr(memory_store, "record_rejection"):
        memory_store.record_rejection(
            user_id,
            gate=gate or "unknown",
            reason=reason,
            context={"approval_id": aid, "symbol": pending.get("symbol"), "args": pending.get("args")},
        )
    memory_store.append_alert_event(
        user_id,
        {
            "kind": "resolution",
            "approval_id": aid,
            "gate": gate,
            "action": action,
            "symbol": pending.get("symbol"),
            "status": action,
            "reason": reason or None,
        },
    )
    _logger.info("HITL %s %s id=%s → %s", action, gate, aid, out.get("status"))
    return ReviewResult(ok=True, action=action, approval_id=aid, gate=gate, next_status=out.get("status"))


def approve_pending(
    approval_id: str,
    *,
    memory_store: MemoryStore,
    resume: ResumeFn,
    user_id: str = "default",
) -> ReviewResult:
    return _review(approval_id, True, "", memory_store=memory_store, resume=resume, user_id=user_id)


def reject_pending(
    approval_id: str,
    reason: str,
    *,
    memory_store: MemoryStore,
    resume: ResumeFn,
    user_id: str = "default",
) -> ReviewResult:
    why = (reason or "").strip()
    if not why:
        return ReviewResult(ok=False, action="rejected", approval_id=approval_id or "", error="lý do reject rỗng")
    return _review(approval_id, False, why, memory_store=memory_store, resume=resume, user_id=user_id)
