"""HITL Feedback Telemetry Service.

Exports comprehensive feedback records to resources/data/hitl_feedback.json.
Captures question, answer, trace, duration, tokens, rating, reason, and feedback comment.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import sqlite3

from backend.database.repositories import MessageRepository


def get_hitl_feedback_json_path() -> Path:
    """Resolve destination file path for hitl_feedback.json."""
    raw = os.environ.get("HITL_FEEDBACK_JSON_PATH")
    if raw:
        path = Path(raw)
    else:
        # Default path relative to project root
        root = Path(__file__).resolve().parents[3]
        path = root / "resources" / "data" / "hitl_feedback.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def record_hitl_telemetry(
    conn: sqlite3.Connection,
    eval_id: str,
    message_id: str,
    session_id: str,
    rating: int | None,
    is_positive: bool,
    reason: str | None,
    user_feedback: str | None,
    created_at: str | None = None,
) -> dict[str, Any]:
    """Extract context from SQLite messages and append telemetry entry to hitl_feedback.json."""
    m_repo = MessageRepository(conn)
    
    # 1. Retrieve the assistant message
    assistant_msg = m_repo.get(message_id) if message_id else None
    
    # 2. Retrieve the user question in this session (the user message preceding the assistant message)
    question = ""
    session_msgs = m_repo.list_by_session(session_id)
    if assistant_msg:
        # Find the message right before assistant_msg
        for i, m in enumerate(session_msgs):
            if m.id == assistant_msg.id:
                # Look backwards for the closest user message
                for prev_idx in range(i - 1, -1, -1):
                    if session_msgs[prev_idx].role == "user":
                        question = session_msgs[prev_idx].content
                        break
                break
    if not question:
        # Fallback to the latest user message in session
        for m in reversed(session_msgs):
            if m.role == "user":
                question = m.content
                break

    answer = assistant_msg.content if assistant_msg else ""
    pipeline_trace = None
    execution_duration_s = None
    tokens_used = None

    if assistant_msg and assistant_msg.trace_data:
        try:
            trace_obj = json.loads(assistant_msg.trace_data)
            pipeline_trace = trace_obj
            steps = trace_obj.get("steps") or []
            # Calculate total duration from steps if available
            total_dur = 0.0
            for s in steps:
                dur = s.get("duration_s")
                if dur is not None:
                    total_dur += float(dur)
            if total_dur > 0:
                execution_duration_s = round(total_dur, 3)
        except Exception:
            pipeline_trace = assistant_msg.trace_data

    # Rough estimate of tokens used if not tracked in trace
    if answer or question:
        tokens_used = max(10, int((len(question) + len(answer)) / 3.5))

    ts = created_at or datetime.now(timezone.utc).isoformat()

    record = {
        "id": eval_id,
        "timestamp": ts,
        "session_id": session_id,
        "message_id": message_id,
        "question": question,
        "answer": answer,
        "pipeline_trace": pipeline_trace,
        "execution_duration_s": execution_duration_s,
        "tokens_used": tokens_used,
        "rating": rating,
        "is_positive": is_positive,
        "reason": reason,
        "user_feedback": user_feedback,
    }

    # Atomic read-and-write to hitl_feedback.json
    json_path = get_hitl_feedback_json_path()
    current_data = []
    if json_path.is_file():
        try:
            content = json_path.read_text(encoding="utf-8").strip()
            if content:
                loaded = json.loads(content)
                if isinstance(loaded, list):
                    current_data = loaded
        except Exception:
            current_data = []

    # Update existing record if eval_id matches, else append
    idx = next((i for i, r in enumerate(current_data) if r.get("id") == eval_id), -1)
    if idx >= 0:
        current_data[idx] = record
    else:
        current_data.append(record)

    # Write back to JSON file
    temp_path = json_path.with_suffix(".tmp")
    temp_path.write_text(json.dumps(current_data, ensure_ascii=False, indent=2), encoding="utf-8")
    temp_path.replace(json_path)

    return record
