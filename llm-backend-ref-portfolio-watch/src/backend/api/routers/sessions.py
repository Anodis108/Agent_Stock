"""REST API router for Session management in Portfolio Watch V4.

Provides endpoints:
- GET    /api/v1/sessions             : List all sessions sorted by updated_at DESC
- POST   /api/v1/sessions             : Create a new conversation session
- GET    /api/v1/sessions/{session_id}: Get session details and message history
- DELETE /api/v1/sessions/{session_id}: Delete a session and all its messages
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from backend.database.connection import get_connection
from backend.database.repositories import (
    MessageRecord,
    MessageRepository,
    SessionRecord,
    SessionRepository,
)

router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])
alias_router = APIRouter(prefix="/api/sessions", tags=["sessions-alias"])


class SessionOut(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str


class SessionListResponse(BaseModel):
    items: list[SessionOut] = Field(default_factory=list)
    count: int = 0


class CreateSessionRequest(BaseModel):
    title: str | None = "Cuộc trò chuyện mới"


class MessageOut(BaseModel):
    id: str
    session_id: str
    role: str
    content: str
    chart_path: str | None = None
    trace_data: str | None = None
    created_at: str


class SessionDetailResponse(BaseModel):
    session: SessionOut
    messages: list[MessageOut] = Field(default_factory=list)
    message_count: int = 0


def _list_sessions(limit: int = 50) -> SessionListResponse:
    conn = get_connection()
    try:
        repo = SessionRepository(conn)
        records = repo.list_all(limit=limit)
        items = [
            SessionOut(
                id=r.id,
                title=r.title,
                created_at=r.created_at,
                updated_at=r.updated_at,
            )
            for r in records
        ]
        return SessionListResponse(items=items, count=len(items))
    finally:
        conn.close()


def _create_session(body: CreateSessionRequest | None = None) -> SessionOut:
    title = (body.title if body and body.title else "Cuộc trò chuyện mới").strip() or "Cuộc trò chuyện mới"
    conn = get_connection()
    try:
        repo = SessionRepository(conn)
        record = repo.create(title=title)
        return SessionOut(
            id=record.id,
            title=record.title,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )
    finally:
        conn.close()


def _get_session_detail(session_id: str) -> SessionDetailResponse:
    conn = get_connection()
    try:
        s_repo = SessionRepository(conn)
        m_repo = MessageRepository(conn)

        session = s_repo.get(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Session không tồn tại")

        raw_msgs = m_repo.list_by_session(session_id)
        messages = [
            MessageOut(
                id=m.id,
                session_id=m.session_id,
                role=m.role,
                content=m.content,
                chart_path=m.chart_path,
                trace_data=m.trace_data,
                created_at=m.created_at,
            )
            for m in raw_msgs
        ]
        return SessionDetailResponse(
            session=SessionOut(
                id=session.id,
                title=session.title,
                created_at=session.created_at,
                updated_at=session.updated_at,
            ),
            messages=messages,
            message_count=len(messages),
        )
    finally:
        conn.close()


def _delete_session(session_id: str) -> dict[str, Any]:
    conn = get_connection()
    try:
        repo = SessionRepository(conn)
        existing = repo.get(session_id)
        if existing is None:
            raise HTTPException(status_code=404, detail="Session không tồn tại")
        repo.delete(session_id)
        return {"status": "deleted", "session_id": session_id}
    finally:
        conn.close()


# /api/v1/sessions endpoints
@router.get("", response_model=SessionListResponse)
def list_sessions(limit: int = Query(default=50, ge=1, le=200)) -> SessionListResponse:
    return _list_sessions(limit=limit)


@router.post("", response_model=SessionOut, status_code=201)
def create_session(body: CreateSessionRequest | None = None) -> SessionOut:
    return _create_session(body=body)


@router.get("/{session_id}", response_model=SessionDetailResponse)
def get_session(session_id: str) -> SessionDetailResponse:
    return _get_session_detail(session_id=session_id)


@router.delete("/{session_id}")
def delete_session(session_id: str) -> dict[str, Any]:
    return _delete_session(session_id=session_id)


# /api/sessions alias endpoints for convenience
@alias_router.get("", response_model=SessionListResponse)
def alias_list_sessions(limit: int = Query(default=50, ge=1, le=200)) -> SessionListResponse:
    return _list_sessions(limit=limit)


@alias_router.post("", response_model=SessionOut, status_code=201)
def alias_create_session(body: CreateSessionRequest | None = None) -> SessionOut:
    return _create_session(body=body)


@alias_router.get("/{session_id}", response_model=SessionDetailResponse)
def alias_get_session(session_id: str) -> SessionDetailResponse:
    return _get_session_detail(session_id=session_id)


@alias_router.delete("/{session_id}")
def alias_delete_session(session_id: str) -> dict[str, Any]:
    return _delete_session(session_id=session_id)
