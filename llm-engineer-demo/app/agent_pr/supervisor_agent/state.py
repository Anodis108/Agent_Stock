"""SupervisorState — blackboard của Hierarchical Coordinator (Sơ đồ 3).

Khác bản pipeline cũ (mọi worker ghi thẳng lên cùng 1 state): mỗi worker là
SUBGRAPH riêng. LangGraph chỉ copy field TRÙNG TÊN giữa SupervisorState và
cửa sổ worker — `rows` của craw/news, `quote`, `report`, `result` nội bộ
không lộ lên hub. Đó là ranh giới cơ chế, giống hierarchical.py.

Không nhét `rows` / `quote` / `report` vào đây — craw và news cùng tên `rows`
sẽ đè nhau nếu share 1 blackboard.
"""

from __future__ import annotations

from typing import Annotated, Any, TypedDict


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
from app.agent_pr.db_agent.schemas import CandidateNews
from app.agent_pr.eval_agent.schemas import Agent_Output as EvalOut
from app.agent_pr.news_agent.schemas import Agent_Output as NewsOut
from app.agent_pr.supervisor_agent.schemas import Agent_Output, AgentPlan
from app.agent_pr.synthesis_agent.schemas import Agent_Output as SynthOut


class SupervisorState(TypedDict, total=False):
    """total=False: coordinator / worker chỉ trả field mình ghi.

    `output` (không đặt tên `result`) — synth/db subgraph cũng ghi `result`,
    trùng tên sẽ lẫn kiểu Pydantic khi nhúng.
    """

    symbol: Annotated[str, _last]
    question: str
    turn: str                      # uuid mỗi HTTP — tách plan/eval/synth khỏi checkpoint cũ
    user_id: str                   # long-term: rỗng = không recall/store
    history: Annotated[list, _append_trim]  # short-term; compact ghi đè qua set_history
    memories: list[str]            # long-term đã recall lượt này
    plan: AgentPlan
    plan_turn: str
    next_wave: str
    price: PriceOut
    news: NewsOut
    db: DbOut
    eval: EvalOut
    eval_turn: str
    n_history: int
    draft: SynthOut
    synth_turn: str
    output: Agent_Output
    trace: list[str]
    # Không có `_trace_span` trên hub — checkpointer không serialize được
    # LangfuseSpan. Hub lấy span qua tracing.current_span(); worker nhận qua Send.


class PriceWindow(TypedDict, total=False):
    """Cửa sổ PriceAgent. `rows`/`quote` ở lại đây, hub chỉ thấy `price`."""

    symbol: str
    rows: list[dict[str, Any]]     # nội bộ craw — không có trên SupervisorState
    quote: PriceOut                # craw parse ghi
    price: PriceOut                # lift copy quote → tên hub dùng
    _trace_span: Any               # trùng tên hub → craw subgraph nhận span cha


class EvalWindow(TypedDict, total=False):
    """Cửa sổ EvalAgent. `report` nội bộ → `eval` cho hub."""

    price: PriceOut
    news: NewsOut
    report: EvalOut
    eval: EvalOut
    turn: str                      # copy từ hub — lift ghi eval_turn
    eval_turn: str
    _trace_span: Any


class SynthWindow(TypedDict, total=False):
    """Cửa sổ Synthesis. `result` nội bộ → `draft` (tránh đụng output của hub)."""

    price: PriceOut
    news: NewsOut
    eval: EvalOut
    n_history: int
    result: SynthOut
    draft: SynthOut
    turn: str
    synth_turn: str
    _trace_span: Any


class DbWindow(TypedDict, total=False):
    """Cửa sổ DBAgent. `result` nội bộ → `db` (tránh đụng output của hub)."""

    symbol: str
    candidate_news: list[CandidateNews]
    price_rows: list[dict[str, Any]]
    news_rows: list[dict[str, Any]]
    pending_rows: list[dict[str, Any]]
    result: DbOut                  # db graph ghi
    db: DbOut                      # lift
    _trace_span: Any
