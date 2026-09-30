"""REST API router for Human-In-The-Loop (HITL) Answer Evaluation & Feedback in Portfolio Watch V4.

Provides endpoints:
- POST /api/v1/hitl/feedback : Submit answer evaluation (thumbs up/down, 1-5 rating, text feedback)
- GET  /api/v1/hitl/feedbacks: Retrieve list of evaluations (optionally filtered by session_id)
- GET  /api/v1/hitl/feedback/{eval_id}: Retrieve single evaluation by ID

Aliases:
- /api/hitl/*
- /hitl/*
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from backend.database.connection import get_connection
from backend.database.repositories import HITLEvaluationRepository, SessionRepository
from backend.services.hitl_service import record_hitl_telemetry

router = APIRouter(prefix="/api/v1/hitl", tags=["hitl"])
alias_router = APIRouter(prefix="/api/hitl", tags=["hitl-alias"])
direct_router = APIRouter(prefix="/hitl", tags=["hitl-direct"])


class FeedbackCreateRequest(BaseModel):
    """Payload to submit answer evaluation & user feedback."""

    message_id: str | None = None
    session_id: str | None = None
    is_positive: bool = True
    rating: int | None = Field(default=None, ge=1, le=5)
    feedback_text: str | None = None
    feedback: str | None = None
    reason: str | None = None
    question: str | None = None
    answer: str | None = None


class FeedbackOut(BaseModel):
    """Normalized feedback record output."""

    id: str
    message_id: str | None = None
    session_id: str | None = None
    rating: int | None = None
    feedback: str | None = None
    feedback_text: str | None = None
    is_positive: bool = True
    reason: str | None = None
    question: str | None = None
    answer: str | None = None
    created_at: str


class FeedbackListResponse(BaseModel):
    """Collection response for HITL evaluations."""

    items: list[FeedbackOut] = Field(default_factory=list)
    count: int = 0


def _create_feedback_record(body: FeedbackCreateRequest) -> FeedbackOut:
    """Save feedback into SQLite hitl_evaluations table and export JSON telemetry."""
    conn = get_connection()
    try:
        repo = HITLEvaluationRepository(conn)
        fb_content = body.feedback_text if body.feedback_text is not None else body.feedback

        # Default rating if not explicitly specified
        effective_rating = body.rating
        if effective_rating is None:
            effective_rating = 5 if body.is_positive else 1

        # Ensure session exists to satisfy foreign key constraint
        sid = body.session_id or "default"
        sess_repo = SessionRepository(conn)
        if not sess_repo.get(sid):
            sess_repo.create(title="Cuộc trò chuyện", session_id=sid)

        from backend.database.repositories import MessageRepository
        m_repo = MessageRepository(conn)
        
        question = body.question
        answer = body.answer
        
        if not question or not answer:
            assistant_msg = m_repo.get(body.message_id) if body.message_id else None
            
            if not question:
                session_msgs = m_repo.list_by_session(sid)
                if assistant_msg:
                    for i, m in enumerate(session_msgs):
                        if m.id == assistant_msg.id:
                            for prev_idx in range(i - 1, -1, -1):
                                if session_msgs[prev_idx].role == "user":
                                    question = session_msgs[prev_idx].content
                                    break
                            break
                if not question:
                    for m in reversed(session_msgs):
                        if m.role == "user":
                            question = m.content
                            break

            if not answer:
                answer = assistant_msg.content if assistant_msg else ""
                
        rec = repo.create(
            message_id=body.message_id or "",
            session_id=sid,
            is_positive=body.is_positive,
            rating=effective_rating,
            feedback=fb_content,
            reason=body.reason,
            question=question,
            answer=answer,
        )

        # Export rich telemetry to resources/data/hitl_feedback.json
        try:
            record_hitl_telemetry(
                conn=conn,
                eval_id=rec.id,
                message_id=rec.message_id,
                session_id=rec.session_id,
                rating=rec.rating,
                is_positive=rec.is_positive,
                reason=rec.reason,
                question=rec.question,
                answer=rec.answer,
                user_feedback=rec.feedback,
                created_at=rec.created_at,
            )
        except Exception as e:
            # Telemetry export error should not fail the user's feedback submission
            pass

        return FeedbackOut(
            id=rec.id,
            message_id=rec.message_id,
            session_id=rec.session_id,
            rating=rec.rating,
            feedback=rec.feedback,
            feedback_text=rec.feedback,
            is_positive=rec.is_positive,
            reason=rec.reason,
            question=rec.question,
            answer=rec.answer,
            created_at=rec.created_at,
        )
    finally:
        conn.close()


def _list_feedbacks_data(session_id: str | None = None, limit: int = 100) -> FeedbackListResponse:
    """Query feedbacks from SQLite."""
    conn = get_connection()
    try:
        repo = HITLEvaluationRepository(conn)
        if session_id:
            records = repo.list_by_session(session_id)
        else:
            records = repo.list_all(limit=limit)

        items = [
            FeedbackOut(
                id=r.id,
                message_id=r.message_id,
                session_id=r.session_id,
                rating=r.rating,
                feedback=r.feedback,
                feedback_text=r.feedback,
                is_positive=r.is_positive,
                reason=r.reason,
                question=r.question,
                answer=r.answer,
                created_at=r.created_at,
            )
            for r in records
        ]
        return FeedbackListResponse(items=items, count=len(items))
    finally:
        conn.close()


def _get_feedback_by_id(eval_id: str) -> FeedbackOut:
    """Retrieve single feedback record by evaluation ID."""
    conn = get_connection()
    try:
        repo = HITLEvaluationRepository(conn)
        rec = repo.get(eval_id)
        if not rec:
            raise HTTPException(status_code=404, detail=f"Feedback '{eval_id}' not found")
        return FeedbackOut(
            id=rec.id,
            message_id=rec.message_id,
            session_id=rec.session_id,
            rating=rec.rating,
            feedback=rec.feedback,
            feedback_text=rec.feedback,
            is_positive=rec.is_positive,
            reason=rec.reason,
            question=rec.question,
            answer=rec.answer,
            created_at=rec.created_at,
        )
    finally:
        conn.close()


# Register endpoints across primary and alias routers
for r in (router, alias_router, direct_router):

    @r.post("/feedback", response_model=FeedbackOut, status_code=200)
    def post_feedback(body: FeedbackCreateRequest) -> FeedbackOut:
        return _create_feedback_record(body)

    @r.get("/feedbacks", response_model=FeedbackListResponse)
    def get_feedbacks(
        session_id: str | None = Query(None, description="Lọc theo session ID"),
        limit: int = Query(100, ge=1, le=500, description="Số lượng bản ghi tối đa"),
    ) -> FeedbackListResponse:
        return _list_feedbacks_data(session_id=session_id, limit=limit)

    @r.get("/feedback/{eval_id}", response_model=FeedbackOut)
    def get_feedback_detail(eval_id: str) -> FeedbackOut:
        return _get_feedback_by_id(eval_id)
