"""Agent eval scorers — ý tưởng từ llm-engineer-demo/app/agent_pr/eval.py.

task_success: chấm kết quả cuối vs nhiệm vụ.
trajectory: chấm chuỗi bước multi-agent (diagnostic; không gate cứng MVP).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, Field

from backend.infra.llm.completion import chat_parsed
from backend.infra.llm.params import DETERMINISTIC
from backend.shared.settings import settings

JUDGE_MODEL = "gpt-4o-mini"
TASK_SUCCESS_SLICES = frozenset({"lookup", "comparison"})
TRAJECTORY_WARN_THRESHOLD = 3.0


class TaskSuccessResult(BaseModel):
    success: bool = Field(description="Có hoàn thành đúng yêu cầu không")
    score: float = Field(ge=0.0, le=1.0, description="Điểm hoàn thành 0-1")
    reasoning: str = Field(description="Giải thích ngắn cho kết luận")


class TrajectoryResult(BaseModel):
    efficiency: int = Field(ge=1, le=5, description="Có bước thừa/lặp không")
    logical_order: int = Field(ge=1, le=5, description="Thứ tự bước hợp lý")
    tool_correctness: int = Field(ge=1, le=5, description="Đúng agent/tool + tham số")
    recovery: int = Field(ge=1, le=5, description="Xử lý lỗi (5 nếu không lỗi)")
    issues: list[str] = Field(default_factory=list)

    @property
    def overall(self) -> float:
        return (
            self.efficiency
            + self.logical_order
            + self.tool_correctness
            + self.recovery
        ) / 4.0


class AgentEvalResult(BaseModel):
    task_success: TaskSuccessResult
    trajectory: TrajectoryResult
    step_count: int


from backend.infra.llm.prompt_registry import registry

_DEFAULT_TASK_SUCCESS_SYSTEM = """Bạn là giám khảo đánh giá trợ lý hỏi–đáp cổ phiếu Việt Nam
(Portfolio Watch).

Chỉ chấm KẾT QUẢ CUỐI so với nhiệm vụ — không chấm đường đi agent.
Rubric tuyệt đối: không thưởng câu dài.

Đạt mục tiêu khi câu trả lời:
- nêu đúng mã được hỏi (nếu câu hỏi có mã)
- khớp phạm vi nhiệm vụ (chỉ hỏi giá → không bắt buộc tin; hỏi tin → không bắt buộc %)
- grounded: không bịa mã/số liệu
- tiếng Việt, rõ; thiếu dữ liệu mà agent nói thiếu vẫn đạt nếu đúng phạm vi
- không đưa lời khuyên mua/bán chắc chắn"""

_SUCCESS_CRITERIA = (
    "Câu trả lời tiếng Việt, đúng mã/phạm vi câu hỏi, không bịa số liệu, "
    "không khuyên mua/bán chắc chắn."
)

_DEFAULT_TRAJECTORY_SYSTEM = """Bạn chấm CHUỖI HÀNH ĐỘNG của multi-agent Portfolio Watch
(không chỉ câu trả lời cuối).

Luồng hợp lý điển hình: rewrite_question → supervisor (chọn agent) →
price_agent và/hoặc news_agent (và eval_agent nếu cần giải thích) →
answer_composer → (guardrail nếu có).

Trừ điểm nếu: gọi eval khi chưa có giá/tin cần thiết; lặp agent thừa;
sai mã CP; bỏ qua agent cần thiết cho phạm vi câu hỏi.

4 tiêu chí ĐỘC LẬP, thang 1-5. Ít bước vì câu hỏi đơn giản là ĐÚNG
(efficiency), không phải thiếu sót."""


def _get_task_success_system_prompt() -> str:
    try:
        return registry().get("eval_task_success").template.strip()
    except Exception:
        return _DEFAULT_TASK_SUCCESS_SYSTEM


def _get_trajectory_system_prompt() -> str:
    try:
        return registry().get("eval_trajectory").template.strip()
    except Exception:
        return _DEFAULT_TRAJECTORY_SYSTEM


def evaluate_task_success(
    task: str,
    final_output: str,
    success_criteria: str = "",
    *,
    chat_parsed_fn: Callable[..., Any] | None = None,
) -> TaskSuccessResult:
    parts = [
        f"Nhiệm vụ: {task}",
        f"Kết quả agent trả về: {final_output}",
        f"Tiêu chí thành công: {success_criteria or _SUCCESS_CRITERIA}",
    ]
    messages = [
        {"role": "system", "content": _get_task_success_system_prompt()},
        {"role": "user", "content": "\n\n".join(parts)},
    ]
    parse = chat_parsed_fn or chat_parsed
    prev = settings.llm_model
    settings.llm_model = JUDGE_MODEL
    try:
        return parse(messages, TaskSuccessResult, DETERMINISTIC)
    finally:
        settings.llm_model = prev


def evaluate_trajectory(
    task: str,
    trajectory: list[dict],
    *,
    chat_parsed_fn: Callable[..., Any] | None = None,
) -> TrajectoryResult:
    if not trajectory:
        formatted = "(không có bước nào)"
    else:
        lines = []
        for i, step in enumerate(trajectory):
            tool = step.get("tool") or step.get("name") or "?"
            args = step.get("args") or {}
            obs = str(step.get("observation") or step.get("detail") or "")[:200]
            lines.append(f"Bước {i + 1}: gọi {tool}({args}) → {obs}")
        formatted = "\n".join(lines)
    messages = [
        {"role": "system", "content": _get_trajectory_system_prompt()},
        {
            "role": "user",
            "content": f"Nhiệm vụ: {task}\n\nChuỗi hành động:\n{formatted}",
        },
    ]
    parse = chat_parsed_fn or chat_parsed
    prev = settings.llm_model
    settings.llm_model = JUDGE_MODEL
    try:
        return parse(messages, TrajectoryResult, DETERMINISTIC)
    finally:
        settings.llm_model = prev


def evaluate_run(
    task: str,
    final_output: str,
    trajectory: list[dict],
    *,
    success_criteria: str = "",
    chat_parsed_fn: Callable[..., Any] | None = None,
) -> AgentEvalResult:
    return AgentEvalResult(
        task_success=evaluate_task_success(
            task,
            final_output,
            success_criteria,
            chat_parsed_fn=chat_parsed_fn,
        ),
        trajectory=evaluate_trajectory(
            task, trajectory, chat_parsed_fn=chat_parsed_fn
        ),
        step_count=len(trajectory),
    )


def steps_from_answer_result(result: Any) -> list[dict]:
    """Dựng trajectory từ AnswerQuestionResult.steps (chat) hoặc field cũ."""
    existing = getattr(result, "steps", None) or []
    if existing:
        out: list[dict] = []
        for s in existing:
            if isinstance(s, dict) and "tool" in s:
                out.append(s)
            elif isinstance(s, dict):
                out.append(
                    {
                        "tool": s.get("name") or "?",
                        "args": {},
                        "observation": s.get("detail") or "",
                    }
                )
            else:
                out.append(
                    {
                        "tool": getattr(s, "name", "?"),
                        "args": {},
                        "observation": getattr(s, "detail", "") or "",
                    }
                )
        return out

    steps: list[dict] = []
    rewritten = getattr(result, "rewritten", None)
    if rewritten is not None:
        steps.append(
            {
                "tool": "rewrite_question",
                "args": {"symbol": getattr(rewritten, "symbol", None)},
                "observation": getattr(rewritten, "rewritten", "") or "",
            }
        )
    routing = getattr(result, "routing", None)
    if routing is not None:
        agents = list(getattr(routing, "agents_to_call", None) or [])
        steps.append(
            {
                "tool": "supervisor",
                "args": {"agents": agents},
                "observation": getattr(routing, "reason", "") or str(
                    getattr(routing, "route", "")
                ),
            }
        )
    price = getattr(result, "price", None)
    if price is not None:
        steps.append(
            {
                "tool": "price_agent",
                "args": {"symbol": getattr(price, "symbol", None)},
                "observation": (
                    f"close={getattr(price, 'latest_close', None)} "
                    f"chg={getattr(price, 'change_pct', None)} "
                    f"err={getattr(price, 'error', None)}"
                ),
            }
        )
    news = getattr(result, "news", None)
    if news is not None:
        n = len(getattr(news, "items", None) or [])
        steps.append(
            {
                "tool": "news_agent",
                "args": {"symbol": getattr(news, "symbol", None)},
                "observation": f"items={n} err={getattr(news, 'error', None)}",
            }
        )
    ev = getattr(result, "eval_result", None)
    if ev is not None:
        sev = getattr(ev, "severity", None)
        steps.append(
            {
                "tool": "eval_agent",
                "args": {},
                "observation": str(sev) if sev is not None else str(ev),
            }
        )
    answer = getattr(result, "answer", None)
    if answer is not None:
        steps.append(
            {
                "tool": "answer_composer",
                "args": {},
                "observation": str(answer)[:200],
            }
        )
    return steps
