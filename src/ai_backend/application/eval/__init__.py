"""Eval package for AI Backend Microservice.

Bao gồm:
- gate: Kiểm tra và chặn merge khi điểm kiểm chuẩn tụt quá ngưỡng.
- history: Lưu lịch sử chạy eval và đo noise (σ).
- regression: Full golden regression test runner.
- agent_eval: Đánh giá chất lượng toàn diện của Multi-Agent Swarm.
- eval_cache: Cache kết quả eval tránh gọi LLM dư thừa.
- steps: Chuẩn hóa cấu trúc steps và gắn trạng thái lỗi.
- run, run_detailed, run_excel_export: Bộ công cụ chạy benchmark và xuất báo cáo.
"""

from ai_backend.application.eval.agent_eval import (
    AgentEvalSummary,
    CaseAgentEvalResult,
    export_eval_report,
    run_agent_eval,
)
from ai_backend.application.eval.gate import (
    GATES,
    GateCheck,
    GateResult,
    check_gates,
    load_gate_report,
)

__all__ = [
    "AgentEvalSummary",
    "CaseAgentEvalResult",
    "export_eval_report",
    "run_agent_eval",
    "GATES",
    "GateCheck",
    "GateResult",
    "check_gates",
    "load_gate_report",
]
