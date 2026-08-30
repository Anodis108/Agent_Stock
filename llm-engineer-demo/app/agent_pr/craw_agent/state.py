"""CrawlState — bảng dữ liệu chung của graph craw_agent.

State chảy qua 3 node: normalize → fetch → parse. Mỗi node nhận state, trả
partial dict; LangGraph merge vào state chính (giống GraphState ở app/agent).

Khác app/agent: không có Send/fan-out, không reducer `operator.add`. Graph
tuyến tính — mỗi field chỉ một node ghi, không hội tụ song song nên không cần
tách raw_* / * để tránh cộng trùng.
"""

from __future__ import annotations

from typing import Any, TypedDict

from app.agent_pr.craw_agent.schemas import Agent_Output


class CrawlState(TypedDict, total=False):
    """State xuyên suốt graph lấy giá.

    total=False: node chỉ trả field nó thực sự cập nhật, không phải khai đủ
    mọi key mỗi lần (normalize chỉ trả symbol; fetch chỉ trả rows).
    """

    symbol: str                    # mã đã upper + nằm ALLOWED (normalize ghi)
    rows: list[dict[str, Any]]     # [{time, close}, ...] từ vnstock; close = nghìn đồng
    quote: Agent_Output            # parse ghi; run_crawl lấy đúng field này trả caller
    _trace_span: Any               # span cha LangFuse — Send/cửa sổ phải truyền (xem GraphState)
