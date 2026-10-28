"""LLM client dùng chung cho 4 pattern multi-agent — Module II, Bài 6.

Tách riêng khỏi nodes.py (agent đơn, Bài 2-5) vì multi-agent không cần tool
retrieval (Bài 4) — mỗi agent con ở đây chỉ bind ĐÚNG tool của domain mình
(xem tools.py: TOOL_GROUPS), không phải chọn lọc qua embedding similarity.
"""

from __future__ import annotations


def base_llm():
    """Client chưa bind tool — dùng lại `agents/nodes._base_llm` (settings + LLM backend của project,
    đã cache 1 lần) thay cho `app.config` của llm-engineer-demo."""
    from ai_backend.domain.agents.nodes import _base_llm

    return _base_llm()
