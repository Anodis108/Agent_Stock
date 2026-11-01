"""Evaluators — map `app/eval_pipeline/scorers.py` (rule + LLM judge trên từng case)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, Field

from ai_backend.domain.guardrails.output_checks import find_buy_sell_phrases
from ai_backend.infra.cache.tiered import chat_parsed_cached
from ai_backend.infra.eval.agent_scorers import (
    TASK_SUCCESS_SLICES,
    TRAJECTORY_WARN_THRESHOLD,
    TaskSuccessResult,
    TrajectoryResult,
    evaluate_task_success,
    evaluate_trajectory,
)
from ai_backend.infra.llm.params import DETERMINISTIC
from ai_backend.infra.prompts import get_system_prompt
from common.settings import settings

# Model chốt sẵn cho judge (Lesson17 / test-plan) — không đổi theo request ad-hoc.
JUDGE_MODEL = "gpt-4o-mini"
JUDGE_SLICES = frozenset({"lookup", "comparison"})
RULE_SLICES = frozenset(
    {
        "lookup",
        "news",
        "indicator",
        "comparison",
        "portfolio",
        "watchlist",
        "chart",
        "out_of_scope",
        "injection",
        "disclaimer",
        "explain_why",
        "charting_diagram",
        "session_memory",
        "diagram",
    }
)
# Điểm trung bình >= ngưỡng → pass (rubric 1–5). Không được hạ dưới sàn này.
JUDGE_PASS_THRESHOLD = 3.0
JUDGE_PASS_THRESHOLD_MIN = 3.0
REGRESSION_TOLERANCE = 0.05
REGRESSION_TOLERANCE_MAX = REGRESSION_TOLERANCE


class RuleBasedScore(BaseModel):
    """Kết quả chấm rule-based cho một output."""

    passed: bool
    missing: list[str] = Field(default_factory=list)
    forbidden_found: list[str] = Field(default_factory=list)

    def as_dict(self) -> dict:
        return self.model_dump()


class LlmJudgeScore(BaseModel):
    """Rubric tuyệt đối — pattern judge.py (llm-backend-ref), 3 tiêu chí theo spec."""

    correctness: int = Field(
        ge=1,
        le=5,
        description="Điểm số thang 1-5 (5 là hoàn toàn chính xác, 1 là hoàn toàn sai)",
    )
    completeness: int = Field(
        ge=1,
        le=5,
        description="Điểm số thang 1-5 (5 là trả lời đầy đủ, 1 là thiếu ý)",
    )
    grounding: int = Field(
        ge=1,
        le=5,
        description="Điểm số thang 1-5 (5 là hoàn toàn bám sát căn cứ/expected, 1 là bịa đặt)",
    )
    reasoning: str = Field(description="Giải thích ngắn cho điểm số")

    @property
    def overall(self) -> float:
        return (self.correctness + self.completeness + self.grounding) / 3.0


class LlmJudgeResult(BaseModel):
    """Kết quả judge kèm trạng thái skip (tiết kiệm chi phí LLM)."""

    skipped: bool
    skip_reason: str | None = None
    score: LlmJudgeScore | None = None
    passed: bool | None = None

    def as_dict(self) -> dict:
        return {
            "skipped": self.skipped,
            "skip_reason": self.skip_reason,
            "score": None
            if self.score is None
            else {
                "correctness": self.score.correctness,
                "completeness": self.score.completeness,
                "grounding": self.score.grounding,
                "overall": self.score.overall,
                "reasoning": self.score.reasoning,
            },
            "passed": self.passed,
        }


def _get_judge_system_prompt() -> str:
    return get_system_prompt("eval_judge")


def score_rule_based(
    output: str,
    must_include: list[str] | None = None,
    must_not_include: list[str] | None = None,
) -> RuleBasedScore:
    """Substring check (case-insensitive) trên output thật (cả 5 slice)."""
    text = (output or "").lower()
    missing = [p for p in (must_include or []) if p and p.lower() not in text]
    forbidden_found = [
        p for p in (must_not_include or []) if p and p.lower() in text
    ]
    return RuleBasedScore(
        passed=not missing and not forbidden_found,
        missing=missing,
        forbidden_found=forbidden_found,
    )


def score_case_rule_based(case: dict, output: str) -> RuleBasedScore:
    """Chấm một case golden; out_of_scope thêm cụm Guardrail Output."""
    score = score_rule_based(
        output,
        must_include=case.get("must_include") or [],
        must_not_include=case.get("must_not_include") or [],
    )
    slice_type = (case.get("slice") or {}).get("type")
    if slice_type == "out_of_scope":
        already = {p.lower() for p in score.forbidden_found}
        for pat in find_buy_sell_phrases(output or ""):
            if pat not in already:
                score.forbidden_found.append(pat)
        if score.forbidden_found:
            score.passed = False
    return score


def score_llm_judge(
    question: str,
    answer: str,
    *,
    expected: str | None = None,
    context: str | None = None,
    chat_parsed_fn: Callable[..., Any] | None = None,
) -> LlmJudgeScore:
    """Gọi LLM-as-judge (temperature=0, model=JUDGE_MODEL)."""
    parts = [f"Câu hỏi: {question}", f"Câu trả lời cần chấm: {answer}"]
    if expected:
        parts.append(f"Expected / tham khảo: {expected}")
    if context:
        parts.append(f"Context / evidence (grounding): {context}")
    messages = [
        {"role": "system", "content": _get_judge_system_prompt()},
        {"role": "user", "content": "\n\n".join(parts)},
    ]
    parse = chat_parsed_fn or chat_parsed_cached
    prev_model = settings.llm_model
    settings.llm_model = JUDGE_MODEL
    try:
        return parse(messages, LlmJudgeScore, DETERMINISTIC)
    finally:
        settings.llm_model = prev_model


def score_case_llm_judge(
    case: dict,
    output: str,
    rule_score: RuleBasedScore,
    *,
    context: str | None = None,
    chat_parsed_fn: Callable[..., Any] | None = None,
) -> LlmJudgeResult:
    """Judge chỉ cho lookup/comparison khi rule-based đã pass."""
    slice_type = (case.get("slice") or {}).get("type")
    if slice_type not in JUDGE_SLICES:
        return LlmJudgeResult(
            skipped=True,
            skip_reason=f"slice={slice_type!r} không dùng LLM-judge",
        )
    if not rule_score.passed:
        return LlmJudgeResult(
            skipped=True,
            skip_reason="rule-based failed — bỏ qua LLM-judge (tiết kiệm chi phí)",
        )
    score = score_llm_judge(
        case.get("question") or "",
        output,
        expected=case.get("expected"),
        context=context,
        chat_parsed_fn=chat_parsed_fn,
    )
    return LlmJudgeResult(
        skipped=False,
        score=score,
        passed=score.overall >= JUDGE_PASS_THRESHOLD,
    )


def assert_scorer_locks(
    *,
    judge_threshold: float | None = None,
    tolerance: float | None = None,
) -> None:
    """Không nới scorer: ngưỡng judge ≥ sàn; tolerance ≤ trần đã chốt."""
    jt = JUDGE_PASS_THRESHOLD if judge_threshold is None else float(judge_threshold)
    if jt < JUDGE_PASS_THRESHOLD_MIN - 1e-12:
        raise ValueError(
            f"Không được nới JUDGE_PASS_THRESHOLD dưới {JUDGE_PASS_THRESHOLD_MIN} "
            f"(đang {jt})"
        )
    if JUDGE_PASS_THRESHOLD < JUDGE_PASS_THRESHOLD_MIN - 1e-12:
        raise ValueError(
            f"JUDGE_PASS_THRESHOLD khóa = {JUDGE_PASS_THRESHOLD} "
            f"< sàn {JUDGE_PASS_THRESHOLD_MIN}"
        )
    tol = REGRESSION_TOLERANCE if tolerance is None else float(tolerance)
    if tol > REGRESSION_TOLERANCE_MAX + 1e-12:
        raise ValueError(
            f"Không được nới --tolerance trên {REGRESSION_TOLERANCE_MAX} "
            f"(đang {tol}) — sửa hệ thống hoặc ghi blocked + Phase 3c"
        )


class TaskSuccessEval(BaseModel):
    """Wrapper task_success (có thể skip để tiết kiệm LLM)."""

    skipped: bool
    skip_reason: str | None = None
    result: TaskSuccessResult | None = None

    def as_dict(self) -> dict:
        return {
            "skipped": self.skipped,
            "skip_reason": self.skip_reason,
            "result": None if self.result is None else self.result.model_dump(),
        }


class TrajectoryEval(BaseModel):
    """Wrapper trajectory — MVP chỉ cảnh báo, không gate pass case."""

    skipped: bool
    skip_reason: str | None = None
    result: TrajectoryResult | None = None
    warn: bool = False

    def as_dict(self) -> dict:
        return {
            "skipped": self.skipped,
            "skip_reason": self.skip_reason,
            "warn": self.warn,
            "result": None
            if self.result is None
            else {
                **self.result.model_dump(),
                "overall": self.result.overall,
            },
        }


def score_case_task_success(
    case: dict,
    output: str,
    rule: RuleBasedScore,
    *,
    chat_parsed_fn: Callable[..., Any] | None = None,
    skip: bool = False,
) -> TaskSuccessEval:
    """task_success cho lookup/comparison khi rule đã pass."""
    slice_type = (case.get("slice") or {}).get("type")
    if skip:
        return TaskSuccessEval(skipped=True, skip_reason="skip_agent_eval=True")
    if slice_type not in TASK_SUCCESS_SLICES:
        return TaskSuccessEval(
            skipped=True,
            skip_reason=f"slice={slice_type!r} không dùng task_success",
        )
    if not rule.passed:
        return TaskSuccessEval(
            skipped=True,
            skip_reason="rule-based failed — bỏ qua task_success",
        )
    result = evaluate_task_success(
        case.get("question") or "",
        output,
        success_criteria=case.get("expected") or "",
        chat_parsed_fn=chat_parsed_fn,
    )
    return TaskSuccessEval(skipped=False, result=result)


def score_case_trajectory(
    case: dict,
    steps: list[dict],
    *,
    chat_parsed_fn: Callable[..., Any] | None = None,
    skip: bool = False,
) -> TrajectoryEval:
    """Trajectory diagnostic — warn nếu overall < ngưỡng."""
    if skip:
        return TrajectoryEval(skipped=True, skip_reason="skip_agent_eval=True")
    result = evaluate_trajectory(
        case.get("question") or "",
        steps,
        chat_parsed_fn=chat_parsed_fn,
    )
    return TrajectoryEval(
        skipped=False,
        result=result,
        warn=result.overall < TRAJECTORY_WARN_THRESHOLD,
    )
