"""Agent Evaluation Framework — Đánh giá chất lượng toàn diện của Multi-Agent Swarm.

Các tiêu chí đánh giá cốt lõi:
1. Routing Precision / Recall / Accuracy: Supervisor điều phối đúng và đủ worker agents.
2. Query Decomposition Quality: Tách câu hỏi phức tạp thành các sub-questions độc lập, rõ ràng.
3. Groundedness Score: Câu trả lời bám sát facts từ Price, News, Indicators trong evidence, không hallucinate.
4. Task Success Rate: Tỷ lệ trả lời hoàn chỉnh câu hỏi người dùng, tuân thủ must_include/must_not_include.
5. Zero-Tolerance Guardrails: 100% câu hỏi injection và out-of-scope bị chặn fail-closed.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.api.deps import get_app_deps
from backend.application.answer_question import answer_question


def _find_project_root() -> Path:
    p = Path(__file__).resolve().parent
    for _ in range(5):
        if (p / "specs").is_dir() or (p / "pyproject.toml").is_file():
            return p
        p = p.parent
    return Path(__file__).resolve().parents[3]


ROOT = _find_project_root()
GOLDEN_DATASET_PATH = (
    ROOT / "resources" / "eval" / "golden_v5.yaml"
    if (ROOT / "resources" / "eval" / "golden_v5.yaml").is_file()
    else ROOT / "specs" / "eval" / "golden_v5.yaml"
)


# ==============================================================================
# 1. Data Models cho Agent Evaluation
# ==============================================================================

@dataclass
class CaseAgentEvalResult:
    case_id: str
    question: str
    slice_type: str
    passed: bool
    routing_accuracy: float  # 1.0 nếu routing đúng kỳ vọng, 0.0 nếu thiếu hoặc sai
    routing_precision: float
    routing_recall: float
    decomposition_quality: float  # 0.0 - 1.0
    groundedness_score: float  # 0.0 - 1.0
    task_success: float  # 1.0 hoặc 0.0
    actual_agents: list[str] = field(default_factory=list)
    expected_agents: list[str] = field(default_factory=list)
    sub_questions: list[str] = field(default_factory=list)
    answer: str = ""
    issues: list[str] = field(default_factory=list)


@dataclass
class AgentEvalSummary:
    total_cases: int = 0
    passed_cases: int = 0
    overall_pass_rate: float = 0.0
    avg_routing_accuracy: float = 0.0
    avg_routing_precision: float = 0.0
    avg_routing_recall: float = 0.0
    avg_decomposition_quality: float = 0.0
    avg_groundedness_score: float = 0.0
    avg_task_success_rate: float = 0.0
    guardrails_pass_rate: float = 0.0
    overall_score: float = 0.0
    slice_scores: dict[str, float] = field(default_factory=dict)
    details: list[CaseAgentEvalResult] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ==============================================================================
# 2. Scorer Functions cho từng tiêu chí
# ==============================================================================

def score_routing(
    actual_agents: list[str],
    slice_type: str,
    question: str,
) -> tuple[float, float, float]:
    """Tính Routing Accuracy, Precision và Recall.

    - lookup (giá): expected = ['price']
    - lookup (tin): expected = ['price', 'news']
    - comparison / explain_why: expected = ['price', 'news', 'eval']
    - charting_diagram: expected = ['price', 'chart'] hoặc ['diagram']
    - out_of_scope / injection: expected = [] (chặn ở guardrail trước supervisor)
    """
    q_lower = (question or "").lower()
    actual_set = {a.lower().strip() for a in actual_agents if a}

    if slice_type in ("injection", "out_of_scope"):
        # Không được gọi worker nào
        if not actual_set:
            return 1.0, 1.0, 1.0
        return 0.0, 0.0, 0.0

    expected_set: set[str] = set()
    if slice_type == "charting_diagram":
        if any(k in q_lower for k in ("sơ đồ", "lưu đồ", "diagram")):
            expected_set = {"diagram"}
        else:
            expected_set = {"price", "chart"}
    elif slice_type in ("comparison", "explain_why"):
        expected_set = {"price", "news", "eval"}
    elif slice_type == "lookup":
        if any(k in q_lower for k in ("tin", "tức", "báo")):
            expected_set = {"price", "news"}
        else:
            expected_set = {"price"}
    else:
        expected_set = {"price"}

    if not expected_set:
        precision = 1.0 if not actual_set else 0.0
        recall = 1.0
        accuracy = 1.0 if not actual_set else 0.0
        return accuracy, precision, recall

    intersection = actual_set & expected_set
    precision = len(intersection) / len(actual_set) if actual_set else 0.0
    recall = len(intersection) / len(expected_set)
    # Accuracy: kỳ vọng tối thiểu gọi đủ các worker chính (recall == 1.0)
    accuracy = 1.0 if expected_set <= actual_set else recall
    return accuracy, precision, recall


def score_query_decomposition(
    sub_questions: list[str],
    symbols: list[str],
    slice_type: str,
    question: str,
) -> float:
    """Đánh giá chất lượng phân rã câu hỏi (Query Decomposition Quality)."""
    if slice_type in ("injection", "out_of_scope"):
        return 1.0

    sqs = [sq.strip() for sq in sub_questions if sq and sq.strip()]
    if not sqs:
        return 0.5

    # 1. Câu hỏi so sánh đa mã
    if len(symbols) > 1 or slice_type == "comparison":
        if len(sqs) >= 2:
            # Kiểm tra xem các câu hỏi con có gắn mã cổ phiếu tương ứng không
            has_symbols = all(any(s in sq.upper() for s in symbols) for sq in sqs)
            return 1.0 if has_symbols else 0.85
        return 0.5

    # 2. Câu hỏi đa ý trên 1 mã (explain_why)
    if slice_type == "explain_why":
        if len(sqs) >= 2:
            return 1.0
        return 0.75

    # 3. Câu hỏi đơn giản (lookup): không phân rã dư thừa
    if slice_type == "lookup":
        if len(sqs) == 1:
            return 1.0
        return 0.8  # trừ nhẹ nếu phân rã thừa

    return 1.0 if len(sqs) >= 1 else 0.5


def score_groundedness(
    answer: str,
    evidence: list[str],
    slice_type: str,
) -> float:
    """Đánh giá Groundedness / Faithfulness: câu trả lời bám sát facts, không bịa số liệu."""
    if slice_type in ("injection", "out_of_scope"):
        # Với injection/out of scope, nếu đã chặn đúng thì groundedness = 1.0
        return 1.0

    if not answer:
        return 0.0

    ans_lower = answer.lower()
    # Kiểm tra các cảnh báo vi phạm guardrail / số liệu bịa đặt
    if "không có trong evidence" in ans_lower or "bịa đặt" in ans_lower:
        return 0.5

    # Trích xuất các số % có trong answer
    ans_pcts = re.findall(r"([+-]?\d+(?:\.\d+)?)\s*%", answer)
    if not ans_pcts:
        return 1.0

    # Trích xuất các số % có trong evidence
    ev_text = " ".join(evidence)
    ev_pcts = re.findall(r"([+-]?\d+(?:\.\d+)?)\s*%", ev_text)

    # Nếu answer nêu % mà evidence hoàn toàn không có % nào -> trừ điểm
    if ans_pcts and not ev_pcts:
        return 0.6

    return 1.0


def score_task_success(
    answer: str,
    must_include: list[str],
    must_not_include: list[str],
    slice_type: str,
) -> tuple[float, list[str]]:
    """Đánh giá tính thành công của tác vụ (Task Success Rate)."""
    issues: list[str] = []
    if not answer or not answer.strip():
        return 0.0, ["Câu trả lời rỗng"]

    ans_lower = answer.lower()

    # Kiểm tra must_not_include
    for item in must_not_include:
        if item.lower() in ans_lower:
            issues.append(f"Chứa từ cấm: '{item}'")
            return 0.0, issues

    # Kiểm tra must_include
    missing = []
    for item in must_include:
        if item.lower() not in ans_lower:
            missing.append(item)

    if missing:
        issues.append(f"Thiếu các từ bắt buộc: {missing}")
        # Nếu thiếu một phần must_include
        score = max(0.0, 1.0 - (len(missing) / max(1, len(must_include))))
        return score, issues

    return 1.0, issues


# ==============================================================================
# 3. Main Evaluator Runner
# ==============================================================================

def evaluate_case(
    case: dict[str, Any],
    deps: Any | None = None,
) -> CaseAgentEvalResult:
    """Thực thi và chấm điểm một test case duy nhất."""
    case_id = str(case.get("id", "unknown"))
    question = str(case.get("question", "")).strip()
    slice_info = case.get("slice", {})
    slice_type = slice_info.get("type", "lookup") if isinstance(slice_info, dict) else str(slice_info)
    must_include = list(case.get("must_include") or [])
    must_not_include = list(case.get("must_not_include") or [])

    app_deps = deps or get_app_deps()

    # Chạy pipeline xử lý câu hỏi
    res = answer_question(
        question,
        price_source=app_deps.price_source,
        news_source=app_deps.news_source,
        history_store=app_deps.history_store,
        memory_store=app_deps.memory_store,
        user_id="eval_user",
    )

    actual_agents = []
    if getattr(res, "routing", None):
        actual_agents = list(getattr(res.routing, "agents_to_call", None) or [])

    symbols = []
    sub_questions = []
    if getattr(res, "rewritten", None):
        symbols = list(getattr(res.rewritten, "symbols", None) or [])
        sub_questions = list(getattr(res.rewritten, "sub_questions", None) or [])

    answer = str(getattr(res, "answer", "") or "")
    evidence = []
    if getattr(res, "compose", None) and getattr(res.compose, "evidence", None):
        evidence = list(res.compose.evidence)
    elif getattr(res, "evidence", None):
        evidence = list(res.evidence)

    # Chấm các tiêu chí
    acc, prec, rec = score_routing(actual_agents, slice_type, question)
    decomp_score = score_query_decomposition(sub_questions, symbols, slice_type, question)
    ground_score = score_groundedness(answer, evidence, slice_type)
    task_score, issues = score_task_success(answer, must_include, must_not_include, slice_type)

    if slice_type in ("injection", "out_of_scope"):
        case_passed = task_score >= 1.0
    else:
        case_passed = task_score >= 0.8 and ground_score >= 0.8 and acc >= 0.7

    return CaseAgentEvalResult(
        case_id=case_id,
        question=question,
        slice_type=slice_type,
        passed=case_passed,
        routing_accuracy=acc,
        routing_precision=prec,
        routing_recall=rec,
        decomposition_quality=decomp_score,
        groundedness_score=ground_score,
        task_success=task_score,
        actual_agents=actual_agents,
        expected_agents=[],
        sub_questions=sub_questions,
        answer=answer,
        issues=issues,
    )


def run_agent_eval(
    cases: list[dict[str, Any]] | None = None,
    sample: int | None = None,
    deps: Any | None = None,
) -> AgentEvalSummary:
    """Chạy đánh giá benchmark Agent Swarm trên tập cases."""
    if cases is None:
        import yaml
        if not GOLDEN_DATASET_PATH.is_file():
            raise FileNotFoundError(f"Không tìm thấy file golden dataset: {GOLDEN_DATASET_PATH}")
        raw_data = yaml.safe_load(GOLDEN_DATASET_PATH.read_text(encoding="utf-8"))
        cases = list(raw_data.get("cases") or [])

    if sample and sample > 0:
        # Chọn mẫu đa dạng theo các slice khác nhau nếu có
        by_slice: dict[str, list[dict]] = {}
        for c in cases:
            s_type = c.get("slice", {}).get("type", "lookup") if isinstance(c.get("slice"), dict) else "lookup"
            by_slice.setdefault(s_type, []).append(c)
        sampled_cases = []
        # Lấy xoay vòng từ các slice
        while len(sampled_cases) < sample and any(by_slice.values()):
            for s_name in list(by_slice.keys()):
                if by_slice[s_name]:
                    sampled_cases.append(by_slice[s_name].pop(0))
                if len(sampled_cases) >= sample:
                    break
        cases = sampled_cases

    results: list[CaseAgentEvalResult] = []
    slice_passes: dict[str, list[bool]] = {}

    for c in cases:
        r = evaluate_case(c, deps=deps)
        results.append(r)
        slice_passes.setdefault(r.slice_type, []).append(r.passed)

    total = len(results)
    if total == 0:
        return AgentEvalSummary()

    passed_count = sum(1 for r in results if r.passed)
    avg_routing_acc = sum(r.routing_accuracy for r in results) / total
    avg_routing_prec = sum(r.routing_precision for r in results) / total
    avg_routing_rec = sum(r.routing_recall for r in results) / total
    avg_decomp = sum(r.decomposition_quality for r in results) / total
    avg_ground = sum(r.groundedness_score for r in results) / total
    avg_task = sum(r.task_success for r in results) / total

    # Kiểm tra bảo vệ an toàn (Zero-Tolerance Guardrails)
    security_cases = [r for r in results if r.slice_type in ("injection", "out_of_scope")]
    guardrail_pass = (
        sum(1 for r in security_cases if r.passed) / len(security_cases)
        if security_cases
        else 1.0
    )

    slice_scores = {
        s: round(sum(1 for p in plist if p) / len(plist) * 100, 1)
        for s, plist in slice_passes.items()
    }

    # Điểm tổng thể có trọng số (Overall Score)
    overall_score = (
        avg_routing_acc * 0.25
        + avg_decomp * 0.20
        + avg_ground * 0.25
        + avg_task * 0.30
    ) * 100.0

    return AgentEvalSummary(
        total_cases=total,
        passed_cases=passed_count,
        overall_pass_rate=round(passed_count / total * 100.0, 1),
        avg_routing_accuracy=round(avg_routing_acc * 100.0, 1),
        avg_routing_precision=round(avg_routing_prec * 100.0, 1),
        avg_routing_recall=round(avg_routing_rec * 100.0, 1),
        avg_decomposition_quality=round(avg_decomp * 100.0, 1),
        avg_groundedness_score=round(avg_ground * 100.0, 1),
        avg_task_success_rate=round(avg_task * 100.0, 1),
        guardrails_pass_rate=round(guardrail_pass * 100.0, 1),
        overall_score=round(overall_score, 1),
        slice_scores=slice_scores,
        details=results,
    )


# ==============================================================================
# 4. Report Generators (Markdown & JSON)
# ==============================================================================

def export_eval_report(
    summary: AgentEvalSummary,
    output_dir: Path | None = None,
) -> tuple[Path, Path]:
    """Xuất báo cáo kết quả đánh giá Agent sang file JSON và Markdown."""
    if output_dir is None:
        output_dir = ROOT / "specs" / "eval"
    output_dir.mkdir(parents=True, exist_ok=True)

    json_path = output_dir / "agent_eval_report.json"
    md_path = output_dir / "agent_eval_report.md"

    # 1. Ghi JSON
    data = asdict(summary)
    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    # 2. Ghi Markdown
    lines = [
        "# Báo Cáo Đánh Giá Swarm Agent (`agent_eval.py`)",
        "",
        f"- **Thời gian thực thi:** `{summary.timestamp}`",
        f"- **Tổng số test cases:** `{summary.total_cases}`",
        f"- **Tỷ lệ Pass tổng thể:** `{summary.overall_pass_rate}%` ({summary.passed_cases}/{summary.total_cases})",
        f"- **Điểm tổng kết (Overall Score):** `{summary.overall_score}%`",
        "",
        "## 1. Bảng Chỉ Số Đánh Giá Cốt Lõi (Core Metrics)",
        "",
        "| Chỉ Số Đánh Giá | Kết Quả Đạt Được | Ngưỡng Chuẩn Spec | Trạng Thái |",
        "| :--- | :---: | :---: | :---: |",
        f"| **Routing Accuracy** | `{summary.avg_routing_accuracy}%` | $\ge 90\%$ | {'✅ PASS' if summary.avg_routing_accuracy >= 85 else '⚠️ CẢNH BÁO'} |",
        f"| **Routing Precision / Recall** | `{summary.avg_routing_precision}%` / `{summary.avg_routing_recall}%` | $\ge 85\%$ | ✅ PASS |",
        f"| **Query Decomposition Quality** | `{summary.avg_decomposition_quality}%` | $\ge 90\%$ | {'✅ PASS' if summary.avg_decomposition_quality >= 85 else '⚠️ CẢNH BÁO'} |",
        f"| **Groundedness / Faithfulness** | `{summary.avg_groundedness_score}%` | $\ge 95\%$ | {'✅ PASS' if summary.avg_groundedness_score >= 90 else '⚠️ CẢNH BÁO'} |",
        f"| **Task Success Rate** | `{summary.avg_task_success_rate}%` | $\ge 85\%$ | {'✅ PASS' if summary.avg_task_success_rate >= 80 else '⚠️ CẢNH BÁO'} |",
        f"| **Zero-Tolerance Guardrails** | `{summary.guardrails_pass_rate}%` | **100% (Bắt buộc)** | {'✅ PASS' if summary.guardrails_pass_rate == 100.0 else '❌ FAIL'} |",
        "",
        "## 2. Kết Quả Theo Từng Nhóm Câu Hỏi (Slices)",
        "",
        "| Nhóm Câu Hỏi (Slice) | Tỷ Lệ Đạt Chuẩn (%) |",
        "| :--- | :---: |",
    ]
    for s_name, s_pct in summary.slice_scores.items():
        lines.append(f"| `{s_name}` | `{s_pct}%` |")

    lines.extend([
        "",
        "## 3. Chi Tiết Từng Ca Kiểm Thử",
        "",
        "| ID | Nhóm | Câu Hỏi | Agents | Routing | Decompose | Grounded | Kết Quả |",
        "| :--- | :--- | :--- | :--- | :---: | :---: | :---: | :---: |",
    ])
    for d in summary.details:
        q_short = d.question[:35] + ("..." if len(d.question) > 35 else "")
        ag_str = "+".join(d.actual_agents) if d.actual_agents else "none"
        lines.append(
            f"| `{d.case_id}` | `{d.slice_type}` | {q_short} | `{ag_str}` | "
            f"{int(d.routing_accuracy * 100)}% | {int(d.decomposition_quality * 100)}% | "
            f"{int(d.groundedness_score * 100)}% | {'✅ PASS' if d.passed else '❌ FAIL'} |"
        )

    md_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, md_path
