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

from app.agent_pr.craw_agent.schemas import Agent_Output as PriceOut
from app.agent_pr.db_agent.schemas import Agent_Output as DbOut
from app.agent_pr.db_agent.schemas import CandidateNews
from app.agent_pr.eval_agent.schemas import Agent_Output as EvalOut
from app.agent_pr.news_agent.schemas import Agent_Output as NewsOut
from app.agent_pr.supervisor_agent.schemas import Agent_Output
from app.agent_pr.synthesis_agent.schemas import Agent_Output as SynthOut


class SupervisorState(TypedDict, total=False):
    """total=False: coordinator / worker chỉ trả field mình ghi.

    `output` (không đặt tên `result`) — synth/db subgraph cũng ghi `result`,
    trùng tên sẽ lẫn kiểu Pydantic khi nhúng.
    """

    symbol: Annotated[str, _last]  # 3 worker đợt 1 cùng ghi — xem _last
    next_wave: str                 # wave1 | eval | synth | done — route đọc
    price: PriceOut                # PriceAgent (cửa sổ) ghi
    news: NewsOut                  # NewsAgent ghi (trùng tên NewsState.news)
    db: DbOut                      # DBAgent cửa sổ lift từ result nội bộ
    eval: EvalOut                  # EvalAgent cửa sổ lift từ report
    n_history: int                 # coordinator ghi trước khi giao Synthesis
    draft: SynthOut                # Synthesis cửa sổ lift từ result nội bộ
    output: Agent_Output           # reply đóng gói cho user
    trace: list[str]               # hub ghi từng lượt giao/thu — không reducer
    _trace_span: Annotated[Any, _last]  # span cha LangFuse; 3 worker đợt 1 copy lại — xem _last


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
    report: EvalOut                # eval graph ghi
    eval: EvalOut                  # lift
    _trace_span: Any


class SynthWindow(TypedDict, total=False):
    """Cửa sổ Synthesis. `result` nội bộ → `draft` (tránh đụng output của hub)."""

    price: PriceOut
    news: NewsOut
    eval: EvalOut
    n_history: int
    result: SynthOut               # synth graph ghi
    draft: SynthOut                # lift
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
