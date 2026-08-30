"""DBState — bảng dữ liệu chung của graph db_agent.

State chảy qua 4 node: normalize → read → stage_writes → parse. Mỗi node
nhận state, trả partial dict; LangGraph merge (giống CrawlState / NewsState).

Khác craw_agent/news_agent: có 2 node "việc thật" (read, stage_writes) thay vì
1 (fetch) — vì DBAgent tách rõ ĐỌC (tự động) và SOẠN lệnh ghi (chờ duyệt,
nhưng việc SOẠN thì vẫn tự động — chỉ COMMIT mới cần người, và COMMIT nằm
ngoài graph này, xem graph.py). Vẫn tuyến tính, không Send/fan-out.
"""

from __future__ import annotations

from typing import Any, TypedDict

from app.agent_pr.db_agent.schemas import Agent_Output, CandidateNews


class DBState(TypedDict, total=False):
    """State xuyên suốt graph đọc/soạn-ghi DB.

    total=False: node chỉ trả field nó cập nhật (normalize → symbol;
    read → price_rows/news_rows; stage_writes → pending_rows).
    """

    symbol: str                        # mã đã upper + nằm ALLOWED (normalize ghi)
    candidate_news: list[CandidateNews]  # tin ứng viên cần xét soạn lệnh ghi (đầu vào, giữ nguyên)
    price_rows: list[dict[str, Any]]   # [{trading_date, close}, ...] đọc từ bảng prices
    news_rows: list[dict[str, Any]]    # [{title, url}, ...] đọc từ bảng news (đã duyệt)
    pending_rows: list[dict[str, Any]]  # [{id, symbol, title, url}, ...] vừa soạn, chưa commit
    result: Agent_Output               # parse ghi; run_db lấy đúng field này trả caller
