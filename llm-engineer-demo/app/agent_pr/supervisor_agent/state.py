"""SupervisorState — blackboard của Hierarchical Coordinator (Sơ đồ 3).

Khác bản pipeline cũ (mọi worker ghi thẳng lên cùng 1 state): mỗi worker là
SUBGRAPH riêng. LangGraph chỉ copy field TRÙNG TÊN — `rows`/`quote`/`report`
nội bộ không lộ lên hub. Pack worker ghi `price`/`eval`/`draft`/`db`.

Không nhét `rows` / `quote` / `report` vào đây — craw và news cùng tên `rows`
sẽ đè nhau nếu share 1 blackboard.
"""

from __future__ import annotations

from typing import Annotated, Any, TypedDict

from langgraph.channels.untracked_value import UntrackedValue


def _last(_left, right):
    """3 worker đợt 1 cùng ghi `symbol` (đã upper, cùng giá trị) trong 1 step.

    LastValue mặc định chỉ nhận 1 write/step — không reducer thì
    InvalidUpdateError. Lấy bản sau; mọi nhánh ghi cùng mã.
    """
    return right


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
from app.agent_pr.supervisor_agent.schemas import Agent_Output, AgentPlan
from app.agent_pr.synthesis_agent.schemas import Agent_Output as SynthOut


class SupervisorState(TypedDict, total=False):
    """total=False: node chỉ trả field mình ghi. Subgraph chỉ nhận field trùng tên."""

    # hub — session / context (không worker nào khai)
    question: str                  # câu user gốc (rewrite/history/output)
    rewritten_question: str        # rewrite; recall+plan đọc
    user_id: str                   # Qdrant long-term; rỗng = skip
    history: Annotated[list, _append_trim]  # short-term; compact ghi đè
    memories: list[str]            # recall lượt này; plan đọc
    plan: AgentPlan                # cờ worker; LLM 1 lần/HTTP
    plan_turn: str                 # == turn → không lập plan lại
    next_wave: str                 # db_lookup|gather|eval|synth|db_write|hitl|done
    skip_hitl: bool                # pytest: soạn pending, không interrupt
    turn: str                      # uuid mỗi HTTP; Send db; Eval+Synth cạnh copy → *_turn
    symbol: Annotated[str, _last]  # mã CP; Send: price/news/db; `_last` vì gather 3 nhánh/step
    _trace_span: Annotated[Any, UntrackedValue(object, guard=False)]  # span cha; mọi worker; không checkpoint

    # PriceAgent
    price: PriceOut                # pack ghi; Eval+Synth đọc (cạnh); hub hydrate từ DB

    # NewsAgent
    news: NewsOut                  # pack ghi; Eval+Synth đọc; db_write → candidate_*

    # DBAgent
    db: DbOut                      # pack (lookup/write); hitl/reply đọc pending
    db_lookup_turn: str            # pack khi mode=read; == turn → khỏi đọc lại
    db_write_turn: str             # pack khi mode=write

    # EvalAgent
    eval: EvalOut                  # pack ghi; Synth đọc
    eval_turn: str                 # pack; == turn → khỏi chấm lại

    # SynthesisAgent
    draft: SynthOut                # pack ghi; chỉ reply đọc
    n_history: int                 # số phiên DB; Synth nhận (cạnh, trùng tên)
    synth_turn: str                # pack; == turn → khỏi ghép lại

    # hub — ra HTTP
    output: Agent_Output           # reply ghi; không đặt `result` (trùng db/synth)
    output_issues: list[str]       # guardrail_output: quá ngắn / số lạ / PII / toxic
    trace: list[str]               # log coordinator/after_wave1/reply
