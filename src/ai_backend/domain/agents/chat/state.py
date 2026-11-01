"""State team chat — như scan/state.py: kế thừa AssistantState (graph gốc) + HierarchicalState (supervisor)."""

from __future__ import annotations

import operator
from typing import Annotated, Any

from pydantic import BaseModel, Field

from ai_backend.domain.agents.multi_agent.hierarchical import HierarchicalState
from ai_backend.domain.agents.scan.db_agent.state import DBAgentResult
from ai_backend.domain.agents.state import AssistantState


class RewrittenQuestion(BaseModel):
    """Kết quả rewrite_question: viết lại + decompose (như demo) trong 1 lời gọi LLM structured output."""

    rewritten: str = Field(description="Câu hỏi đầy đủ, tự hiểu được (đã thay đại từ / chỗ lược bằng hội thoại trước)")
    sub_questions: list[str] = Field(
        description="1-4 câu hỏi con, mỗi câu trả lời độc lập được; câu hỏi đơn giản → chỉ 1 phần tử là chính nó"
    )


class ScanResult(BaseModel):
    """Dữ liệu team scan trả về cho chat (scan_team ghi) — thêm field khi node chat cần thêm kết quả scan."""

    db_results: DBAgentResult | None = None  # holdings + watchlist (db_agent) → portfolio_report đọc


class AnswerQuestionResult(BaseModel):
    """Kết quả cuối 1 lượt chat — node answer dựng, start_graph trả về → API / SSE / service."""

    question: str
    answer: str
    drawed_paths: list[str] = Field(default_factory=list)  # ảnh biểu đồ / sơ đồ trên MinIO — UI hiển thị theo đường dẫn


class AnswerEvalData(BaseModel):
    """Dữ liệu chỉ phục vụ eval (routing / decomposition / groundedness) — node answer dựng cùng final_answer."""

    rewritten: RewrittenQuestion | None = None  # None khi guardrail chặn / chào
    agents_called: list[str] = Field(default_factory=list)  # worker đã chạy (key của notes)
    evidence: list[str] = Field(default_factory=list)  # ghi chú worker — dữ kiện answer được phép dùng


class ChatTeamState(AssistantState, HierarchicalState, total=False):
    # AssistantState (graph gốc): messages, user_id, mode, request_id
    # HierarchicalState (supervisor): task, result, notes, next_agent, final_answer
    completed_workers: Annotated[list[str], operator.add]

    # Đầu vào lượt chat (guardrail_input / rewrite_question ghi)
    question: str
    guardrail_result: Any | None
    rewritten: RewrittenQuestion | None  # rewrite_question ghi (None khi chặn / chào)

    # Kết quả worker cần truyền giữa node (còn lại đi qua notes)
    scan_result: ScanResult | None  # scan_team ghi
    drawed: list[str]  # đường dẫn ảnh draw_agent ghi (trùng tên DrawWorkerState) → answer đưa vào final_answer

    # Đầu ra (answer) — start_graph lấy từ update của node answer
    final_answer: AnswerQuestionResult | None
    eval_data: AnswerEvalData | None
