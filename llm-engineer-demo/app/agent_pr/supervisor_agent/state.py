"""SupervisorState — blackboard của Hierarchical Coordinator (bản supervisor/notes).

Cùng mô hình agent_m2 hierarchical.py: `supervisor_node` hỏi LLM sau MỖI worker
để chọn worker tiếp theo, mỗi worker chạy xong gộp kết quả vào `notes[domain]`.

Mỗi worker là SUBGRAPH riêng. LangGraph chỉ copy field TRÙNG TÊN — `rows`/
`quote`/`report` nội bộ không lộ lên hub. Pack worker ghi `price`/`eval`/`db`.

Không nhét `rows` / `quote` / `report` vào đây — craw và news cùng tên `rows`
sẽ đè nhau nếu share 1 blackboard.
"""

from __future__ import annotations

from typing import Annotated, TypedDict


def _append_trim(left, right):
    """Short-term: nối history; compact gửi `set_history` thì GHI ĐÈ.

    Cắt bằng `sliding_window` (giữ system/summary) — không slice đuôi mù,
    kẻo mất bản tóm tắt ở đầu list. Xem app.agent_pr.context.
    """
    from app.agent_pr.context import ReplaceHistory, sliding_window
    from app.config import settings

    if isinstance(right, ReplaceHistory):
        merged = list(right)
    else:
        merged = list(left or []) + list(right or [])
    cap = max(4, int(settings.agent_max_messages))
    return sliding_window(merged, cap)

from app.agent_pr.craw_agent.schemas import Agent_Output as PriceOut
from app.agent_pr.db_agent.schemas import Agent_Output as DbOut
from app.agent_pr.eval_agent.schemas import Agent_Output as EvalOut
from app.agent_pr.news_agent.schemas import Agent_Output as NewsOut
from app.agent_pr.supervisor_agent.schemas import Agent_Output


class SupervisorState(TypedDict, total=False):
    """total=False: node chỉ trả field mình ghi. Subgraph chỉ nhận field trùng tên."""

    # hub — session / context (không worker nào khai)
    question: str                  # câu user gốc (rewrite/history/output)
    rewritten_question: str        # rewrite; recall+supervisor đọc
    symbol: str                    # mã CP; rewrite trích được thì set, worker Send đọc
    user_id: str                   # Qdrant long-term; rỗng = skip
    history: Annotated[list, _append_trim]  # short-term; compact ghi đè
    memories: list[str]            # recall lượt này; supervisor đọc
    skip_hitl: bool                # pytest: soạn pending, không interrupt
    out_of_scope: bool             # guardrail_input: câu ngoài phạm vi — route thẳng reply, bỏ pipeline
    turn: str                      # uuid mỗi HTTP; Send worker đọc để mở đúng span
                                    # cũng là key tra span Langfuse (xem monitoring/tracing.py)

    # Supervisor — routing (giống HierarchicalState của agent_m2)
    notes: dict[str, str]           # domain -> tóm tắt kết quả worker (supervisor đọc để quyết định)
    next_agent: str                 # "price_agent"|"news_agent"|"db_agent"|"db_write"|"eval_agent"|"done"
    final_answer: str               # final_answer_node ghi; reply đọc

    # PriceAgent
    price: PriceOut                # pack ghi; Eval đọc (cạnh)

    # NewsAgent
    news: NewsOut                  # pack ghi; Eval đọc; db_write → candidate_*

    # DBAgent (mode=read: lịch sử; mode=write: soạn pending)
    db: DbOut                      # pack (lookup/write); hitl/reply đọc pending

    # EvalAgent
    eval: EvalOut                  # pack ghi

    # hub — ra HTTP
    output: Agent_Output           # reply ghi
    output_issues: list[str]       # guardrail_output: quá ngắn / số lạ / PII / toxic
    trace: list[str]               # log supervisor/collect/reply
