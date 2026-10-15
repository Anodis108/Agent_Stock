"""HITL (Human-in-the-Loop) Feedback Router for Web Backend."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status

from web_backend.api.deps import AppDeps, get_app_deps, get_current_user_id
from web_backend.api.models.hitl import (
    FeedbackCreateRequest,
    FeedbackListResponse,
    FeedbackOut,
)

router = APIRouter(prefix="/api/v1/hitl", tags=["hitl"])
alias_router = APIRouter(prefix="/api/hitl", tags=["hitl-alias"])
direct_router = APIRouter(prefix="/hitl", tags=["hitl-direct"])

from web_backend.infra.database.connection import get_connection
from web_backend.infra.database.repositories import (
    HITLEvaluationRepository,
    MessageRepository,
    SessionRepository,
)


SIGNAL_SCORE: dict[str, tuple[float, str]] = {
    "thumbs_up": (1.0, "explicit"),
    "thumbs_down": (0.0, "explicit"),
    "copied": (1.0, "implicit"),
    "regenerated": (0.0, "implicit"),
    "abandoned": (0.0, "implicit"),
}


def score_for_signal(reason: str | None) -> tuple[float | None, str | None]:
    if not reason:
        return None, None
    return SIGNAL_SCORE.get(reason, (None, None))


def _to_feedback_out(row: Any) -> FeedbackOut:
    return FeedbackOut(
        id=row.id,
        message_id=getattr(row, "message_id", None),
        session_id=getattr(row, "session_id", None),
        rating=getattr(row, "rating", None),
        feedback=getattr(row, "feedback", None),
        feedback_text=getattr(row, "feedback_text", None),
        is_positive=bool(getattr(row, "is_positive", True)),
        reason=getattr(row, "reason", None),
        question=getattr(row, "question", None),
        answer=getattr(row, "answer", None),
        signal_score=getattr(row, "signal_score", None),
        feedback_source=getattr(row, "feedback_source", None),
        created_at=str(getattr(row, "created_at", "")),
    )


def _create_feedback_record(body: FeedbackCreateRequest) -> FeedbackOut:
    conn = get_connection()
    try:
        s_repo = SessionRepository(conn)
        m_repo = MessageRepository(conn)
        repo = HITLEvaluationRepository(conn)

        sid = (body.session_id or "").strip()
        if not sid or s_repo.get(sid) is None:
            session = s_repo.create(title=body.question or "Đánh giá HITL", session_id=sid or None)
            sid = session.id

        mid = (body.message_id or "").strip()
        if not mid or m_repo.get(mid) is None:
            msg = m_repo.create(
                session_id=sid,
                role="assistant",
                content=body.answer or "",
                message_id=mid or None,
            )
            mid = msg.id

        fb_content = body.feedback_text if body.feedback_text is not None else body.feedback
        score, source = score_for_signal(body.reason)

        record = repo.create(
            message_id=mid,
            session_id=sid,
            is_positive=body.is_positive,
            rating=body.rating,
            feedback=fb_content,
            reason=body.reason,
            question=body.question,
            answer=body.answer,
            signal_score=score,
            feedback_source=source,
        )
        return _to_feedback_out(record)
    finally:
        conn.close()


@router.post("/feedback", response_model=FeedbackOut, status_code=status.HTTP_201_CREATED)
@alias_router.post("/feedback", response_model=FeedbackOut, status_code=status.HTTP_201_CREATED)
@direct_router.post("/feedback", response_model=FeedbackOut, status_code=status.HTTP_201_CREATED)
def create_feedback(
    body: FeedbackCreateRequest,
    current_user_id: str = Depends(get_current_user_id),
    deps: AppDeps = Depends(get_app_deps),
) -> FeedbackOut:
    return _create_feedback_record(body)


@router.get("/feedbacks", response_model=FeedbackListResponse)
@alias_router.get("/feedbacks", response_model=FeedbackListResponse)
@direct_router.get("/feedbacks", response_model=FeedbackListResponse)
@router.get("/feedback", response_model=FeedbackListResponse)
@alias_router.get("/feedback", response_model=FeedbackListResponse)
@direct_router.get("/feedback", response_model=FeedbackListResponse)
def list_feedback(
    session_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    deps: AppDeps = Depends(get_app_deps),
) -> FeedbackListResponse:
    conn = get_connection()
    try:
        repo = HITLEvaluationRepository(conn)
        rows = repo.list_all(session_id=session_id, limit=limit, offset=offset)
        items = [_to_feedback_out(r) for r in rows]
        return FeedbackListResponse(items=items, count=len(items))
    finally:
        conn.close()
