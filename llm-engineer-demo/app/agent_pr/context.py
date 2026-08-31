"""Context engineering — Hierarchical VN-stock (`agent_pr`).

Cùng chiến lược `app.agent_m2.context` (Bài 3, Section 2-4), khác chỗ
*áp vào đâu*:

  agent_m2: list LangChain `messages` trên 1 ReAct agent (sliding mỗi vòng
            tool, compact persist vì ToolNode làm history phình).
  agent_pr: list dict `{role, content}` trên hub (`SupervisorState.history`).
            Worker là subgraph, không nhét ToolMessage vào hub — history
            chỉ cặp user/assistant. Vẫn compact vì nhiều lượt hỏi +
            checkpointer giữ xuyên session.

Không copy BaseMessage: history hub luôn là dict. Mọi lời gọi LLM ở đây
dùng native `completion.chat` — không LangChain.

Trên graph: `compact_history` (persist) đứng sau `recall_memory`, trước
`coordinator`. `_make_plan` chỉ shape TẠM (sliding + reinject) — giống
tách compact_node / agent_node ở agent_m2.
"""

from __future__ import annotations

from app.llm import completion
from app.llm.params import GenerationParams

# Ước lượng thô 1 token ≈ 4 ký tự — đủ nguyên tắc 40-60%, không cần tiktoken.
_CHARS_PER_TOKEN = 4


class ReplaceHistory(list):
    """Marker cho reducer `_merge_history`: GHI ĐÈ list, không nối.

    compact_history phải thay cả history bằng [summary]+recent. Reducer
    mặc định của hub là append — không có marker này thì summary bị
    *cộng thêm* vào đuôi, history càng dài.
    """


def set_history(messages: list) -> ReplaceHistory:
    """Bọc list để compact_history ghi đè state.history."""
    return ReplaceHistory(messages)


def _text_of(m) -> str:
    """Content dạng text — history hub là dict; giữ nhánh object cho chắc."""
    if isinstance(m, dict):
        return str(m.get("content", ""))
    return str(getattr(m, "content", ""))


def _role_of(m) -> str:
    if isinstance(m, dict):
        return str(m.get("role", ""))
    return str(getattr(m, "type", "") or getattr(m, "role", ""))


def format_messages(messages: list) -> str:
    """List message → text đưa vào prompt (plan / store_memory)."""
    return "\n".join(f"{_role_of(m)}: {_text_of(m)}" for m in messages)


# ── Section 2: Sliding window ─────────────────────────────────────────────────


def sliding_window(messages: list, max_messages: int = 20) -> list:
    """Giữ N message gần nhất. System (kể cả bản tóm tắt) luôn được giữ.

    Không đủ dài → trả nguyên. System đã nằm trong `recent` không nhân đôi.
    """
    if len(messages) <= max_messages:
        return list(messages)
    system_msgs = [m for m in messages if _role_of(m) == "system"]
    recent = messages[-max_messages:]
    recent_ids = {id(m) for m in recent}
    return [m for m in system_msgs if id(m) not in recent_ids] + recent


# ── Section 4: Ước lượng + nguyên tắc 40-60% ──────────────────────────────────


def estimate_tokens(messages: list) -> int:
    """Token thô theo ký tự. Đủ để quyết định compact, không phải billing."""
    return sum(len(_text_of(m)) for m in messages) // _CHARS_PER_TOKEN


def context_usage(messages: list, window_tokens: int) -> float:
    """Tỷ lệ 0–1 so với cửa sổ (settings.agent_context_window_tokens)."""
    if window_tokens <= 0:
        return 0.0
    return estimate_tokens(messages) / window_tokens


def should_compact(messages: list, window_tokens: int, threshold: float = 0.40) -> bool:
    """True nếu vượt ngưỡng — compact CHỦ ĐỘNG (Section 4), không đợi đầy 80%."""
    return context_usage(messages, window_tokens) > threshold


# ── Section 2: Summarization ──────────────────────────────────────────────────

SUMMARY_PREFIX = "[Tóm tắt hội thoại trước]:"


def summarize_text(old_messages: list) -> str:
    """LLM tóm 3–5 câu (tên mã, số liệu, quyết định). Tách khỏi state graph
    để test mock `completion.chat` không cần LangGraph.
    """
    prompt = (
        "Tóm tắt hội thoại cổ phiếu sau thành 3-5 câu, giữ mã CP, số liệu, "
        "kết luận đã chốt, câu hỏi đang làm dở:\n\n"
        + format_messages(old_messages)
    )
    return completion.chat(
        [{"role": "user", "content": prompt}], GenerationParams(temperature=0.0)
    )


def summarize_old_messages(messages: list, keep_recent: int = 6) -> list:
    """Phần cũ → 1 system message; giữ `keep_recent` cuối.

    Bản THUẦN (list mới). Trên graph, `compact_history` mới persist qua
    `set_history` — không nén lại mỗi lượt nếu bản nén đã nằm trong state.
    """
    if len(messages) <= keep_recent + 1:
        return list(messages)

    old_messages = messages[:-keep_recent]
    recent_messages = messages[-keep_recent:]
    summary = summarize_text(old_messages)
    summary_msg = {"role": "system", "content": f"{SUMMARY_PREFIX} {summary}"}
    return [summary_msg] + list(recent_messages)


# ── Section 4: Re-injection chống instruction fade-out ────────────────────────


def reinject_instructions(messages: list, instructions: str) -> list:
    """Chèn chỉ dẫn ở CUỐI context (attention cao). System prompt đầu hội
    thoại dài bị lost-in-the-middle — coordinator lập plan cũng vậy.
    """
    return list(messages) + [
        {"role": "system", "content": f"[Nhắc lại chỉ dẫn]: {instructions}"}
    ]
