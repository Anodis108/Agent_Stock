"""Eval runner — map `app/eval_pipeline/runner.py`.

Chạy full golden qua luồng production (`run_graph` mode=chat).
"""

from __future__ import annotations

import asyncio
import os
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from ai_backend.infra.eval.agent_scorers import (
    TASK_SUCCESS_SLICES,
    steps_from_answer_result,
)
from ai_backend.infra.eval.dataset import load_golden_dataset
from ai_backend.infra.eval.scorers import (
    LlmJudgeResult,
    RuleBasedScore,
    TaskSuccessEval,
    TrajectoryEval,
    score_case_llm_judge,
    score_case_rule_based,
    score_case_task_success,
    score_case_trajectory,
)

SLICE_ORDER = (
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
    "diagram",
)


class CaseEvalResult(BaseModel):
    """Kết quả một case: output thật + scorers đã ghép."""

    case_id: str
    slice_type: str
    question: str
    output: str
    rule: RuleBasedScore
    judge: LlmJudgeResult
    passed: bool
    error: str | None = None
    steps: list[dict] = Field(default_factory=list)
    task_success: TaskSuccessEval | None = None
    trajectory: TrajectoryEval | None = None

    def as_dict(self) -> dict:
        return {
            "case_id": self.case_id,
            "slice_type": self.slice_type,
            "question": self.question,
            "output": self.output,
            "rule": self.rule.as_dict(),
            "judge": self.judge.as_dict(),
            "passed": self.passed,
            "error": self.error,
            "steps": self.steps,
            "task_success": None
            if self.task_success is None
            else self.task_success.as_dict(),
            "trajectory": None
            if self.trajectory is None
            else self.trajectory.as_dict(),
        }


class SliceScore(BaseModel):
    slice_type: str
    total: int
    passed: int

    @property
    def rate(self) -> float | None:
        return (self.passed / self.total) if self.total else None

    def as_dict(self) -> dict:
        return {
            "slice_type": self.slice_type,
            "total": self.total,
            "passed": self.passed,
            "failed": self.total - self.passed,
            "rate": self.rate,
        }


class EvalReport(BaseModel):
    """Báo cáo tổng + theo slice + danh sách fail kèm output thật."""

    total: int
    passed: int
    by_slice: list[SliceScore]
    failures: list[CaseEvalResult]

    @property
    def rate(self) -> float:
        return (self.passed / self.total) if self.total else 0.0

    @property
    def failed(self) -> int:
        return self.total - self.passed

    def as_dict(self) -> dict:
        return {
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "rate": self.rate,
            "by_slice": {s.slice_type: s.as_dict() for s in self.by_slice},
            "failures": [
                {
                    "case_id": f.case_id,
                    "slice_type": f.slice_type,
                    "question": f.question,
                    "output": f.output,
                    "error": f.error,
                    "rule": f.rule.as_dict(),
                    "judge": f.judge.as_dict(),
                }
                for f in self.failures
            ],
        }


def case_overall_passed(
    rule: RuleBasedScore,
    judge: LlmJudgeResult,
    *,
    task_success: TaskSuccessEval | None = None,
    slice_type: str = "",
) -> bool:
    """Rule (+ judge nếu chạy) phải pass; lookup/comparison thêm task_success."""
    if not rule.passed:
        return False
    if not judge.skipped and not judge.passed:
        return False
    if slice_type in TASK_SUCCESS_SLICES and task_success is not None:
        if not task_success.skipped and task_success.result is not None:
            if not task_success.result.success and (task_success.result.score or 0.0) < 0.5:
                return False
    return True


def make_answer_fn(
    *,
    price_source: Any | None = None,
    news_source: Any | None = None,
    history_store: Any | None = None,
    memory_store: Any | None = None,
    user_id: str = "eval",
) -> Callable[[str], str]:
    """Bọc `run_graph` (mode=chat) → trả chuỗi answer.

    Gắn `fn.last_steps` (list[dict]) sau mỗi lần gọi để chấm trajectory.
    Không truyền deps → lấy `get_app_deps()` (giống POST /chat).
    """
    from ai_backend.domain.agents.graph import start_graph
    from web_backend.api.deps import get_app_deps

    def _answer(question: str) -> str:
        deps = None
        if (
            price_source is None
            or news_source is None
            or history_store is None
            or memory_store is None
        ):
            deps = get_app_deps()
        req = {
            "price_source": price_source or deps.price_source,
            "news_source": news_source or deps.news_source,
            "history_store": history_store or deps.history_store,
            "memory_store": memory_store or deps.memory_store,
        }

        async def _run() -> Any:
            result = None
            async for kind, payload in start_graph("chat", question, req, user_id=user_id, request_id=f"eval-{uuid4().hex}"):  # eval = điểm vào riêng → sinh request_id ở đây
                if kind == "result":
                    result = payload  # đọc hết generator: save_long_term_memory chạy sau result
            if result is None:
                raise RuntimeError("start_graph không yield result")
            return result

        final = asyncio.run(_run())["final_answer"]
        _answer.last_steps = steps_from_answer_result(final)  # type: ignore[attr-defined]
        return final.answer or ""

    _answer.last_steps = []  # type: ignore[attr-defined]
    return _answer


def _guardrail_template_fingerprint() -> str:
    """Hash guardrail refusal copy — invalidate eval cache when templates change."""
    import hashlib

    path = (
        Path(__file__).resolve().parents[2]
        / "domain"
        / "guardrails"
        / "input_guardrail.py"
    )
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()[:8]
    except OSError:
        return "unknown"


def _eval_cache_prompt_hash(case: dict, *, user_id: str = "eval") -> str:
    from ai_backend.infra.eval.eval_cache import prompt_hash_from_messages
    from ai_backend.infra.prompts import pick_prompt_version
    from common.settings import settings

    question = str(case.get("question") or "")
    base = prompt_hash_from_messages([{"role": "user", "content": question}])
    prompt_version = pick_prompt_version(
        user_id,
        enabled=settings.prompt_ab_enabled,
        version_a=settings.prompt_ab_version_a,
        version_b=settings.prompt_ab_version_b,
        split_pct=settings.prompt_ab_split_pct,
    )
    guardrail_fp = _guardrail_template_fingerprint()
    return f"{base}:{settings.llm_model}:{prompt_version}:{guardrail_fp}"


def eval_one_case(
    case: dict,
    *,
    answer_fn: Callable[[str], str],
    chat_parsed_fn: Callable[..., Any] | None = None,
    agent_eval_parsed_fn: Callable[..., Any] | None = None,
    skip_judge: bool = False,
    skip_agent_eval: bool = False,
) -> CaseEvalResult:
    """Gọi answer_fn → rule → judge → task_success/trajectory."""
    from ai_backend.infra.eval.eval_cache import get_cached, set_cached

    case_id = str(case.get("id") or "")
    slice_type = str((case.get("slice") or {}).get("type") or "")
    question = str(case.get("question") or "")
    output = ""
    error: str | None = None
    prompt_hash = _eval_cache_prompt_hash(case)
    cached = get_cached(case_id, prompt_hash)
    if cached is not None and "output" in cached:
        output = str(cached.get("output") or "")
        error = cached.get("error")
        answer_fn.last_steps = list(cached.get("steps") or [])  # type: ignore[attr-defined]
    else:
        try:
            output = answer_fn(question) or ""
        except (Exception, SystemExit) as exc:  # noqa: BLE001
            error = f"answer_fn error: {exc}"
            output = ""
        set_cached(
            case_id,
            prompt_hash,
            {
                "output": output,
                "error": error,
                "steps": list(getattr(answer_fn, "last_steps", None) or []),
            },
        )

    steps = list(getattr(answer_fn, "last_steps", None) or [])

    rule = score_case_rule_based(case, output)
    if error:
        rule.passed = False
        if not rule.missing and not rule.forbidden_found:
            rule.missing.append("(answer_fn error)")

    if skip_judge:
        judge = LlmJudgeResult(skipped=True, skip_reason="skip_judge=True")
    else:
        judge = score_case_llm_judge(
            case, output, rule, chat_parsed_fn=chat_parsed_fn
        )

    agent_parse = agent_eval_parsed_fn or chat_parsed_fn
    task_success = score_case_task_success(
        case,
        output,
        rule,
        chat_parsed_fn=agent_parse,
        skip=skip_agent_eval,
    )
    trajectory = score_case_trajectory(
        case,
        steps,
        chat_parsed_fn=agent_parse,
        skip=skip_agent_eval,
    )

    return CaseEvalResult(
        case_id=case_id,
        slice_type=slice_type,
        question=question,
        output=output,
        rule=rule,
        judge=judge,
        passed=case_overall_passed(
            rule, judge, task_success=task_success, slice_type=slice_type
        )
        and error is None,
        error=error,
        steps=steps,
        task_success=task_success,
        trajectory=trajectory,
    )


def filter_golden_cases(
    cases: list[dict],
    *,
    case_id: str | None = None,
    limit: int | None = None,
    slice_type: str | None = None,
) -> list[dict]:
    """Lọc theo --case-id, --slice và/hoặc --limit."""
    out = list(cases)
    if case_id:
        out = [c for c in out if str(c.get("id") or "") == case_id]
        if not out:
            raise ValueError(f"unknown case-id: {case_id!r}")
    if slice_type:
        out = [
            c
            for c in out
            if str((c.get("slice") or {}).get("type") or "") == slice_type
        ]
        if not out:
            raise ValueError(f"unknown slice: {slice_type!r}")
    if limit is not None:
        out = out[: max(0, limit)]
    return out


def run_eval(
    cases: list[dict] | None = None,
    *,
    answer_fn: Callable[[str], str] | None = None,
    chat_parsed_fn: Callable[..., Any] | None = None,
    agent_eval_parsed_fn: Callable[..., Any] | None = None,
    skip_judge: bool = False,
    skip_agent_eval: bool = False,
    limit: int | None = None,
    case_id: str | None = None,
    slice_type: str | None = None,
    dataset_path: Path | None = None,
    case_delay_sec: float | None = None,
) -> list[CaseEvalResult]:
    """Runner: duyệt golden cases, gọi answer + ghép scorers từng case.

    `case_delay_sec` / env `EVAL_CASE_DELAY_SEC`: nghỉ giữa case để tránh
    rate-limit vnstock guest khi chạy full golden (Phase 5 regression).
    """
    if cases is None:
        cases = list(load_golden_dataset(dataset_path)["cases"])
    cases = filter_golden_cases(
        cases, case_id=case_id, limit=limit, slice_type=slice_type
    )
    if case_delay_sec is None:
        case_delay_sec = float(os.environ.get("EVAL_CASE_DELAY_SEC", "0") or "0")
    results: list[CaseEvalResult] = []
    for i, case in enumerate(cases):
        if i > 0 and case_delay_sec > 0:
            time.sleep(case_delay_sec)
        # Mỗi case một user_id — tránh memory hội thoại làm lệch rewrite/symbol.
        fn = answer_fn or make_answer_fn(
            user_id=f"eval-{case.get('id') or 'case'}"
        )
        results.append(
            eval_one_case(
                case,
                answer_fn=fn,
                chat_parsed_fn=chat_parsed_fn,
                agent_eval_parsed_fn=agent_eval_parsed_fn,
                skip_judge=skip_judge,
                skip_agent_eval=skip_agent_eval,
            )
        )
    return results


def build_report(results: list[CaseEvalResult]) -> EvalReport:
    """Gộp điểm tổng + theo từng slice; giữ full CaseEvalResult khi fail."""
    total = len(results)
    n_pass = sum(1 for r in results if r.passed)
    counts: dict[str, list[int]] = {s: [0, 0] for s in SLICE_ORDER}  # total, passed
    for r in results:
        key = r.slice_type or "unknown"
        if key not in counts:
            counts[key] = [0, 0]
        counts[key][0] += 1
        if r.passed:
            counts[key][1] += 1
    by_slice: list[SliceScore] = []
    seen = set()
    for s in SLICE_ORDER:
        if s in counts:
            by_slice.append(SliceScore(slice_type=s, total=counts[s][0], passed=counts[s][1]))
            seen.add(s)
    for s, (t, p) in counts.items():
        if s not in seen and t:
            by_slice.append(SliceScore(slice_type=s, total=t, passed=p))
    failures = [r for r in results if not r.passed]
    return EvalReport(
        total=total, passed=n_pass, by_slice=by_slice, failures=failures
    )


def format_report(report: EvalReport, *, output_max: int = 500) -> str:
    """Chuỗi báo cáo đọc được: tổng, slice, rồi từng case fail + output."""
    lines = [
        "=== Eval report ===",
        f"Tổng: {report.passed}/{report.total} passed ({report.rate:.0%})",
        "Theo slice:",
    ]
    for s in report.by_slice:
        if s.total == 0:
            lines.append(f"  - {s.slice_type}: 0/0 passed (n/a)")
        else:
            lines.append(
                f"  - {s.slice_type}: {s.passed}/{s.total} passed ({s.rate:.0%})"
            )
    if not report.failures:
        lines.append("Failures: (none)")
    else:
        lines.append(f"Failures ({len(report.failures)}):")
        for f in report.failures:
            out = f.output or ""
            if len(out) > output_max:
                out = out[:output_max] + "…"
            lines.append(
                f"  - [{f.case_id}] slice={f.slice_type} "
                f"rule={f.rule.passed} judge_skipped={f.judge.skipped} "
                f"judge_passed={f.judge.passed}"
            )
            if f.task_success and not f.task_success.skipped and f.task_success.result:
                ts = f.task_success.result
                lines.append(
                    f"    task_success: success={ts.success} score={ts.score:.2f} "
                    f"— {ts.reasoning[:120]}"
                )
            if f.trajectory and not f.trajectory.skipped and f.trajectory.result:
                tr = f.trajectory.result
                lines.append(
                    f"    trajectory: overall={tr.overall:.2f} warn={f.trajectory.warn}"
                )
            lines.append(f"    question: {f.question}")
            if f.error:
                lines.append(f"    error: {f.error}")
            lines.append(f"    output: {out}")
            if f.rule.missing:
                lines.append(f"    missing: {f.rule.missing!r}")
            if f.rule.forbidden_found:
                lines.append(f"    forbidden: {f.rule.forbidden_found!r}")
    return "\n".join(lines)


def format_trajectory_warnings(results: list[CaseEvalResult]) -> str:
    """In cảnh báo trajectory (overall < ngưỡng) kể cả case đã pass."""
    warns = [
        r
        for r in results
        if r.trajectory
        and not r.trajectory.skipped
        and r.trajectory.warn
    ]
    if not warns:
        return "=== Trajectory warnings ===\n(none)"
    lines = ["=== Trajectory warnings ==="]
    for r in warns:
        tr = r.trajectory.result  # type: ignore[union-attr]
        assert tr is not None
        lines.append(
            f"  - [{r.case_id}] overall={tr.overall:.2f} "
            f"issues={tr.issues!r}"
        )
    return "\n".join(lines)


def format_case_detail(result: CaseEvalResult, *, output_max: int = 800) -> str:
    """Chi tiết một case (dùng với --case-id)."""
    out = result.output or ""
    if len(out) > output_max:
        out = out[:output_max] + "…"
    lines = [
        f"=== Case {result.case_id} ===",
        f"slice: {result.slice_type}",
        f"passed: {result.passed}",
        f"question: {result.question}",
        f"output: {out}",
        f"rule: {result.rule.as_dict()}",
        f"judge: {result.judge.as_dict()}",
        f"steps ({len(result.steps)}): {result.steps!r}",
    ]
    if result.task_success:
        lines.append(f"task_success: {result.task_success.as_dict()}")
    if result.trajectory:
        lines.append(f"trajectory: {result.trajectory.as_dict()}")
    if result.error:
        lines.append(f"error: {result.error}")
    return "\n".join(lines)


def eval_report_to_gate_json(
    report: EvalReport, results: list[CaseEvalResult]
) -> dict:
    """JSON export cho gate.py — gồm by_slice, failures, rule_pass_rate."""
    payload = report.as_dict()
    rule_passed = sum(1 for r in results if r.rule.passed)
    total = len(results)
    payload["rule_passed"] = rule_passed
    payload["rule_total"] = total
    payload["rule_pass_rate"] = (rule_passed / total) if total else 0.0
    return payload
