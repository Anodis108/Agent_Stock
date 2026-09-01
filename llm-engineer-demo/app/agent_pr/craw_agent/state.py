"""CrawlState — bảng dữ liệu chung của graph craw_agent.

State chảy qua 3 node: normalize → fetch → parse. Mỗi node nhận state, trả
partial dict; LangGraph merge vào state chính (giống GraphState ở app/agent).

Khác app/agent: không có Send/fan-out, không reducer `operator.add`. Graph
tuyến tính — mỗi field chỉ một node ghi, không hội tụ song song nên không cần
tách raw_* / * để tránh cộng trùng.
"""

from __future__ import annotations

from typing import Annotated, Any, TypedDict

from langgraph.channels.untracked_value import UntrackedValue
from langgraph.graph.message import add_messages

from app.agent_pr.craw_agent.schemas import Agent_Output


class CrawlState(TypedDict, total=False):
    """State xuyên suốt graph lấy giá.

    total=False: node chỉ trả field nó thực sự cập nhật, không phải khai đủ
    mọi key mỗi lần (normalize chỉ trả symbol; fetch chỉ trả rows).
    """

    symbol: str                    # mã đã upper + đúng định dạng (normalize ghi)
    rows: list[dict[str, Any]]     # [{time, close}, ...] từ vnstock; close = nghìn đồng
    error: str                     # fetch ghi khi IO lỗi — parse đưa vào source, không raise
    quote: Agent_Output            # parse/tool ghi
    price: Agent_Output            # pack copy sang tên field hub
    messages: Annotated[list, add_messages]  # ReAct LLM ⇄ ToolNode
    _trace_span: Annotated[Any, UntrackedValue(object, guard=False)]  # span cha hub — Send phải copy
