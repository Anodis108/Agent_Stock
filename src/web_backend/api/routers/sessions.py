"""REST API router for Session management in Web Backend."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from web_backend.api.models.sessions import (
    CreateSessionRequest,
    MessageOut,
    SessionDetailResponse,
    SessionListResponse,
    SessionOut,
)

router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])
alias_router = APIRouter(prefix="/api/sessions", tags=["sessions-alias"])

from web_backend.infra.database.connection import get_connection
from web_backend.infra.database.repositories import (
    MessageRecord,
    MessageRepository,
    SessionRecord,
    SessionRepository,
)



def _to_session_out(s: Any) -> SessionOut:
    return SessionOut(
        id=s.id,
        title=s.title,
        created_at=s.created_at,
        updated_at=s.updated_at,
    )


def _to_message_out(m: Any) -> MessageOut:
    return MessageOut(
        id=m.id,
        session_id=m.session_id,
        role=m.role,
        content=m.content,
        chart_path=getattr(m, "chart_path", None),
        trace_data=getattr(m, "trace_data", None),
        created_at=m.created_at,
    )


@router.get("", response_model=SessionListResponse)
@alias_router.get("", response_model=SessionListResponse)
def list_sessions(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> SessionListResponse:
    conn = get_connection()
    try:
        repo = SessionRepository(conn)
        sessions = repo.list_all(limit=limit, offset=offset)
        items = [_to_session_out(s) for s in sessions]
        return SessionListResponse(items=items, count=len(items))
    finally:
        conn.close()


@router.post("", response_model=SessionOut, status_code=201)
@alias_router.post("", response_model=SessionOut, status_code=201)
def create_session(body: CreateSessionRequest | None = None) -> SessionOut:
    title = (body.title or "").strip() if body else ""
    title = title or "Cuộc trò chuyện mới"
    conn = get_connection()
    try:
        repo = SessionRepository(conn)
        s = repo.create(title=title)
        return _to_session_out(s)
    finally:
        conn.close()


@router.get("/{session_id}", response_model=SessionDetailResponse)
@alias_router.get("/{session_id}", response_model=SessionDetailResponse)
def get_session(session_id: str) -> SessionDetailResponse:
    conn = get_connection()
    try:
        s_repo = SessionRepository(conn)
        m_repo = MessageRepository(conn)

        s = s_repo.get(session_id)
        if s is None:
            raise HTTPException(status_code=404, detail="Không tìm thấy phiên trò chuyện")

        msgs = m_repo.list_by_session(session_id)
        msg_items = [_to_message_out(m) for m in msgs]

        return SessionDetailResponse(
            session=_to_session_out(s),
            messages=msg_items,
            message_count=len(msg_items),
        )
    finally:
        conn.close()


@router.delete("/{session_id}", status_code=200)
@alias_router.delete("/{session_id}", status_code=200)
def delete_session(session_id: str) -> dict[str, Any]:
    conn = get_connection()
    try:
        s_repo = SessionRepository(conn)
        s = s_repo.get(session_id)
        if s is None:
            raise HTTPException(status_code=404, detail="Không tìm thấy phiên trò chuyện")

        s_repo.delete(session_id)
        return {
            "status": "success",
            "ok": True,
            "deleted_id": session_id,
            "message": "Đã xóa phiên trò chuyện",
        }
    finally:
        conn.close()
