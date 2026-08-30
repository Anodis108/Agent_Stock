"""Agent Evaluation cho Hierarchical Coordinator — cùng 2 chiều với agent_m2/eval.py.

RAGAS/judge.py (Module I) chỉ chấm OUTPUT CUỐI. Agent Hierarchical có thể trả
câu đúng nhưng đi sai Sơ đồ 3d: Eval chạy trước khi có giá+tin, Synthesis tự
crawl, worker nói ngang nhau. File này chấm thêm CON ĐƯỜNG, giống Bài 5:

  - evaluate_task_success : đạt mục tiêu hỏi–đáp mã CP không (không xét quá trình).
  - evaluate_trajectory   : efficiency / logical_order / tool_correctness / recovery
    trên chuỗi hub → worker. Rubric tuyệt đối, không thưởng nhiều bước
    (verbosity bias — xem agent_m2/eval.py).

Khác agent_m2: không có checkpointer/tool_call_id. Trajectory dựng từ
Agent_Output + hub.trace (thứ tự thật: đợt 1 Price·News·DB → Eval → Synthesis).
Khác app/agent_pr/eval_agent/: đó là domain sentiment, không phải LLM-as-judge.

Cost/latency lấy từ LangFuse span `agent_pr_ask` — không nhờ judge.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.llm import completion
from app.llm.params import GenerationParams
from app.agent_pr.supervisor_agent.schemas import Agent_Output


# ── Cùng shape với agent_m2/eval.py — API/UI đọc 1 lần ────────────────────────


class TaskSuccessResult(BaseModel):
    """End-to-end: câu trả lời có đạt yêu cầu hỏi–đáp mã CP không."""

    success: bool = Field(description="Có hoàn thành đúng yêu cầu không")
    score: float = Field(ge=0.0, le=1.0, description="Điểm hoàn thành 0-1")
    reasoning: str = Field(description="Giải thích ngắn cho kết luận")


class TrajectoryResult(BaseModel):
    """4 tiêu chí độc lập (1-5) — không để 1 tiêu chí kéo các tiêu chí còn lại."""

    efficiency: int = Field(ge=1, le=5, description="Có bước thừa/lặp không")
    logical_order: int = Field(ge=1, le=5, description="Thứ tự đợt có đúng Sơ đồ 3d không")
    tool_correctness: int = Field(ge=1, le=5, description="Đúng worker + đúng tham số từng bước")
    recovery: int = Field(ge=1, le=5, description="Có lỗi thì xử lý ra sao (5 nếu không lỗi)")
    issues: list[str] = Field(default_factory=list)

    @property
    def overall(self) -> float:
        return (self.efficiency + self.logical_order + self.tool_correctness + self.recovery) / 4


class AgentEvalResult(BaseModel):
    """Gộp 2 chiều + số bước. Tool accuracy nằm trong trajectory.tool_correctness."""

    task_success: TaskSuccessResult
    trajectory: TrajectoryResult
    step_count: int = Field(description="Số bước trong trajectory đã dựng")


# ── Task success ──────────────────────────────────────────────────────────────

_TASK_SUCCESS_SYSTEM = """Bạn là giám khảo đánh giá Hierarchical Coordinator hỏi–đáp cổ phiếu VN.

Chỉ chấm KẾT QUẢ CUỐI so với nhiệm vụ — không quan tâm hub giao worker nào
(điều đó chấm ở trajectory). Rubric tuyệt đối: không thưởng câu dài, không
so sánh với câu trả lời khác.

Đạt mục tiêu khi câu trả lời:
- nêu đúng mã được hỏi
- có chiều/biến động giá (tăng/giảm + %) hoặc nói rõ thiếu lịch sử
- có thông tin tin tức (số tin / thiên hướng) hoặc nói rõ chưa có tin
- không bịa mã khác, không bịa số liệu không có trong kết quả agent"""

_SUCCESS_CRITERIA = (
    "Câu trả lời tiếng Việt, đúng mã, có biến động giá (hoặc nêu thiếu lịch sử), "
    "có điểm tin/eval (hoặc nêu chưa có tin), không bịa số liệu."
)


def evaluate_task_success(
    task: str, final_output: str, success_criteria: str = ""
) -> TaskSuccessResult:
    """Agent có đạt mục tiêu user không (không xét quá trình)."""
    parts = [
        f"Nhiệm vụ: {task}",
        f"Kết quả agent trả về: {final_output}",
        f"Tiêu chí thành công: {success_criteria or _SUCCESS_CRITERIA}",
    ]
    messages = [
        {"role": "system", "content": _TASK_SUCCESS_SYSTEM},
        {"role": "user", "content": "\n\n".join(parts)},
    ]
    return completion.chat_parsed(messages, TaskSuccessResult, GenerationParams(temperature=0.0))


# ── Trajectory ────────────────────────────────────────────────────────────────

_TRAJECTORY_SYSTEM = """Bạn chấm CHUỖI HÀNH ĐỘNG của Hierarchical Coordinator (Sơ đồ 3d),
không chỉ câu trả lời cuối.

Luồng đúng (cố định, không phải Swarm):
  đợt 1 song song: PriceAgent + NewsAgent + DBAgent
  → hub thu 3 báo cáo
  → đợt 2a EvalAgent (chỉ nhận giá+tin, không crawl)
  → đợt 2b SynthesisAgent (chỉ ghép báo cáo)
  → hub trả user

Trừ điểm logical_order / tool_correctness nếu:
- Eval hoặc Synthesis chạy trước khi đủ giá+tin
- worker tự gọi nhau (cạnh ngang) thay vì báo cáo hub
- Price/News/DB không cùng đợt 1
- worker sai việc (Eval crawl, Synthesis chấm lại sentiment, News tự chấm tốt/xấu)

4 tiêu chí ĐỘC LẬP, thang 1-5. KHÔNG thưởng trajectory dài — nhiều bước hơn
thường là kém hiệu quả (verbosity bias), trừ khi đúng 2 đợt trên map."""


def _format_trajectory(trajectory: list[dict]) -> str:
    if not trajectory:
        return "(không có bước nào)"
    return "\n".join(
        f"Bước {i + 1}: gọi {step['tool']}({step['args']}) → {str(step['observation'])[:200]}"
        for i, step in enumerate(trajectory)
    )


def evaluate_trajectory(task: str, trajectory: list[dict]) -> TrajectoryResult:
    """Chấm toàn bộ chuỗi hub → worker. Cùng 4 tiêu chí agent_m2."""
    messages = [
        {"role": "system", "content": _TRAJECTORY_SYSTEM},
        {
            "role": "user",
            "content": f"Nhiệm vụ: {task}\n\nChuỗi hành động:\n{_format_trajectory(trajectory)}",
        },
    ]
    return completion.chat_parsed(messages, TrajectoryResult, GenerationParams(temperature=0.0))


def evaluate_run(task: str, final_output: str, trajectory: list[dict]) -> AgentEvalResult:
    """Hai lời gọi judge — giống evaluate_run bên agent_m2."""
    return AgentEvalResult(
        task_success=evaluate_task_success(task, final_output),
        trajectory=evaluate_trajectory(task, trajectory),
        step_count=len(trajectory),
    )


# ── Dựng trajectory từ output hub (không có checkpointer như agent_m2) ────────


def extract_trajectory(out: Agent_Output) -> list[dict]:
    """Thứ tự thật trên graph: đợt 1 Price·News·DB → Eval → Synthesis → reply.

    Mỗi bước `{tool, args, observation}` — cùng shape agent_m2._extract_trajectory
    để evaluate_trajectory đọc được. Hub.trace gắn vào observation của
    coordinator để judge thấy lời giao việc, không phải bịa thêm bước.
    """
    hub = " | ".join(out.trace) if out.trace else ""
    steps: list[dict] = [
        {
            "tool": "coordinator",
            "args": {"symbol": out.symbol, "wave": "wave1"},
            "observation": hub or "giao đợt 1 Price · News · DB",
        },
        {
            "tool": "price_agent",
            "args": {"symbol": out.symbol},
            "observation": (
                f"last={out.price.last} prev={out.price.prev_close} "
                f"pct_change={out.price.pct_change} date={out.price.trading_date} "
                f"source={out.price.source}"
            ),
        },
        {
            "tool": "news_agent",
            "args": {"symbol": out.symbol},
            "observation": f"{len(out.news.articles)} tin {out.news.source}",
        },
        {
            "tool": "db_agent",
            "args": {"symbol": out.symbol},
            "observation": out.db.detail if out.db else "chưa gọi DBAgent",
        },
        {
            "tool": "eval_agent",
            "args": {"symbol": out.symbol},
            "observation": out.eval.detail,
        },
        {
            "tool": "synthesis_agent",
            "args": {"symbol": out.symbol},
            "observation": out.answer,
        },
        {
            "tool": "reply",
            "args": {"symbol": out.symbol},
            "observation": f"trả user · {len(out.trace)} dòng trace hub",
        },
    ]
    return steps


def evaluate_ask(out: Agent_Output) -> AgentEvalResult:
    """Chấm 1 lượt /pr/ask đã chạy xong — POST /pr/ask/evaluate."""
    task = f"Phân tích biến động giá và tin tức liên quan đến mã {out.symbol} hôm nay."
    return evaluate_run(task, out.answer, extract_trajectory(out))
