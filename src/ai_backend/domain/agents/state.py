"""Graph state — chia theo tầng (giống agent_m2 hierarchical: supervisor state / worker state).

  AssistantState       (state.py)                      — graph gốc: top_supervisor → chat_team | scan_team
  ChatTeamState        (chat/state.py)                 — subgraph team chat
  ScanHierarchicalState (scan/state.py)                — subgraph team scan (kiêm thu thập dữ liệu cho chat)
  <agent>/state.py     — worker make_agent_graph, kế thừa WorkerState (multi_agent/hierarchical.py)

Team state khai báo lại các field trùng tên AssistantState (messages, user_id, mode, turn) → subgraph nhận/trả đúng các field này;
mọi field khác là nội bộ của team.
"""

from __future__ import annotations

from typing import Annotated, Literal, TypedDict

from langgraph.graph.message import add_messages


class AssistantState(TypedDict, total=False):
    """State xuyên suốt ReAct loop: agent ⇄ tools.

    `Annotated[list, add_messages]` — reducer tự APPEND message mới thay vì
    ghi đè, giữ lịch sử hội thoại qua nhiều vòng agent → tools → agent.

    total=False: `user_id` optional để giữ tương thích ngược với Bài 2 (các
    lời gọi cũ chỉ truyền messages vẫn chạy — recall/store bỏ qua nếu thiếu).
    """

    messages: Annotated[list, add_messages]
    user_id: str  # Bài 3: định danh user để recall/store long-term memory
    mode: Literal["chat", "scan"] # chức năng thực hiện
    request_id: str  # id lượt = LangGraph thread_id (tracing, SSE, HITL resume)
