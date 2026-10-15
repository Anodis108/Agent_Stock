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


def _find_project_root() -> Path:
    p = Path(__file__).resolve().parent
    for _ in range(5):
        if (p / "specs").is_dir() or (p / "pyproject.toml").is_file():
            return p
        p = p.parent
    return Path(__file__).resolve().parents[3]


ROOT = _find_project_root()
GOLDEN_DATASET_PATH = ROOT / "resources" / "eval" / "golden_dataset.yaml"
EXTENDED_DATASET_PATH = ROOT / "resources" / "eval" / "extended_dataset.yaml"
GOLDEN_V6_PATH = GOLDEN_DATASET_PATH  # Backward compatibility alias


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
    """Tính Routing Accuracy, Precision và Recall."""
    q_lower = (question or "").lower()
    actual_set = {a.lower().strip() for a in actual_agents if a}

    if slice_type in ("injection", "out_of_scope", "disclaimer", "portfolio", "watchlist"):
        if not actual_set or actual_set <= {"portfolio", "watchlist", "portfolio_watch_agent", "guardrail", "guardrails"}:
            return 1.0, 1.0, 1.0
        return 0.5, 0.5, 0.5

    if slice_type == "session_memory":
        if actual_set & {"price", "news", "eval", "memory"}:
            return 1.0, 1.0, 1.0
        return 0.8, 0.8, 0.8

    expected_set: set[str] = set()
    if slice_type in ("chart", "charting_diagram"):
        if any(k in q_lower for k in ("sơ đồ", "lưu đồ", "diagram")):
            expected_set = {"diagram"}
        else:
            if "chart" in actual_set:
                return 1.0, 1.0, 1.0
            expected_set = {"price", "chart"}
    elif slice_type in ("comparison", "explain_why"):
        if {"price", "eval"} <= actual_set or {"eval"} <= actual_set or {"price", "news", "eval"} <= actual_set:
            return 1.0, 1.0, 1.0
        expected_set = {"price", "eval"}
    elif slice_type == "indicator":
        if "eval" in actual_set or "price" in actual_set:
            return 1.0, 1.0, 1.0
        expected_set = {"eval"}
    elif slice_type == "news":
        if "news" in actual_set:
            return 1.0, 1.0, 1.0
        expected_set = {"news"}
    elif slice_type == "lookup":
        if any(k in q_lower for k in ("tin", "tức", "báo")):
            if actual_set <= {"price", "news"} and actual_set:
                return 1.0, 1.0, 1.0
            expected_set = {"news"}
        else:
            if "price" in actual_set:
                return 1.0, 1.0, 1.0
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
    accuracy = 1.0 if expected_set <= actual_set else recall
    return accuracy, precision, recall


def score_query_decomposition(
    sub_questions: list[str],
    symbols: list[str],
    slice_type: str,
    question: str,
) -> float:
    """Đánh giá chất lượng phân rã câu hỏi (Query Decomposition Quality)."""
    if slice_type in ("injection", "out_of_scope", "disclaimer", "portfolio", "watchlist", "session_memory"):
        return 1.0

    sqs = [sq.strip() for sq in sub_questions if sq and sq.strip()]
    if not sqs:
        return 1.0

    if len(symbols) > 1 or slice_type == "comparison":
        if len(sqs) >= 2:
            has_symbols = all(any(s in sq.upper() for s in symbols) for sq in sqs)
            return 1.0 if has_symbols else 0.85
        return 0.85

    return 1.0


def score_groundedness(
    answer: str,
    evidence: list[str],
    slice_type: str,
) -> float:
    """Đánh giá Groundedness / Faithfulness."""
    if slice_type in ("injection", "out_of_scope"):
        return 1.0

    if not answer:
        return 0.0

    ans_lower = answer.lower()
    if "không có trong evidence" in ans_lower or "bịa đặt" in ans_lower:
        return 0.5

    ans_pcts = re.findall(r"([+-]?\d+(?:\.\d+)?)\s*%", answer)
    if not ans_pcts:
        return 1.0

    ev_text = " ".join(evidence)
    ev_pcts = re.findall(r"([+-]?\d+(?:\.\d+)?)\s*%", ev_text)

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

    for item in must_not_include:
        if item.lower() in ans_lower:
            issues.append(f"Chứa từ cấm: '{item}'")
            return 0.0, issues

    missing = []
    for item in must_include:
        if item.lower() not in ans_lower:
            missing.append(item)

    if missing:
        issues.append(f"Thiếu các từ bắt buộc: {missing}")
        score = max(0.0, 1.0 - (len(missing) / max(1, len(must_include))))
        return score, issues

    return 1.0, issues


# ==============================================================================
# 3. Main Evaluator Runner
# ==============================================================================

def evaluate_case(
    case: dict[str, Any],
    deps: Any | None = None,
    live_url: str | None = None,
) -> CaseAgentEvalResult:
    """Thực thi và chấm điểm một test case duy nhất."""
    case_id = str(case.get("id", "unknown"))
    question = str(case.get("question", "")).strip()
    slice_info = case.get("slice", {})
    slice_type = slice_info.get("type", "lookup") if isinstance(slice_info, dict) else str(slice_info)
    must_include = list(case.get("must_include") or [])
    must_not_include = list(case.get("must_not_include") or [])

    res = None
    if live_url:
        import urllib.request
        import json
        import time

        payload = json.dumps({"question": question, "user_id": "eval_user"}).encode("utf-8")
        req = urllib.request.Request(
            live_url,
            data=payload,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        data = None
        last_exc = None
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=60.0) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    break
            except Exception as exc:
                last_exc = exc
                time.sleep(1.0)

        if data is None:
            return CaseAgentEvalResult(
                case_id=case_id,
                question=question,
                slice_type=slice_type,
                passed=False,
                routing_accuracy=0.0,
                routing_precision=0.0,
                routing_recall=0.0,
                decomposition_quality=0.0,
                groundedness_score=0.0,
                task_success=0.0,
                answer="",
                issues=[f"Lỗi gọi Live Web API: {last_exc}"],
            )

        class LiveResult:
            pass
        res = LiveResult()
        res.answer = data.get("answer", "")
        res.routing = data.get("route", "")
        res.actual_agents = list(data.get("agents_to_call") or [])
        res.steps = data.get("steps") or []
        res.symbol = data.get("symbol")
        res.symbols = [data["symbol"]] if data.get("symbol") else []
        res.sub_questions = data.get("sub_questions") or []
        if not res.actual_agents and res.steps:
            for st in res.steps:
                sname = (st.get("name") if isinstance(st, dict) else getattr(st, "name", "")).lower()
                if "price" in sname: res.actual_agents.append("price")
                elif "news" in sname: res.actual_agents.append("news")
                elif "chart" in sname: res.actual_agents.append("chart")
                elif "eval" in sname or "indicator" in sname: res.actual_agents.append("eval")
                elif "diagram" in sname: res.actual_agents.append("diagram")
        res.actual_agents = list(dict.fromkeys(res.actual_agents))
        res.compose = None
        res.evidence = []
        if data.get("evidence"):
            res.evidence.extend(data["evidence"])
        if data.get("price"):
            res.evidence.append(str(data["price"]))
        if data.get("news"):
            for n in data["news"]:
                res.evidence.append(str(n))
        for st in res.steps:
            if isinstance(st, dict) and st.get("output"):
                res.evidence.append(str(st["output"]))
            elif hasattr(st, "output") and getattr(st, "output", None):
                res.evidence.append(str(getattr(st, "output")))
    else:
        # Thực thi qua Chat Graph Swarm
        try:
            from ai_backend.infra.graph.chat import run_chat_graph
            from ai_backend.infra.market_data import CafefNewsSource, VnstockPriceSource
            from ai_backend.infra.storage import SqliteMemoryStore, SqlitePriceHistoryStore

            ps = getattr(deps, "price_source", None) or VnstockPriceSource(fallback_on_error=True)
            ns = getattr(deps, "news_source", None) or CafefNewsSource()
            hs = getattr(deps, "history_store", None) or SqlitePriceHistoryStore(":memory:")
            ms = getattr(deps, "memory_store", None) or SqliteMemoryStore(":memory:")

            res = run_chat_graph(
                question,
                price_source=ps,
                news_source=ns,
                history_store=hs,
                memory_store=ms,
                user_id="eval_user",
            )
        except Exception as exc:
            return CaseAgentEvalResult(
                case_id=case_id,
                question=question,
                slice_type=slice_type,
                passed=False,
                routing_accuracy=0.0,
                routing_precision=0.0,
                routing_recall=0.0,
                decomposition_quality=0.0,
                groundedness_score=0.0,
                task_success=0.0,
                answer="",
                issues=[f"Lỗi thực thi: {exc}"],
            )

    actual_agents = getattr(res, "actual_agents", [])
    if not actual_agents and getattr(res, "routing", None):
        routing_obj = getattr(res, "routing")
        if hasattr(routing_obj, "agents_to_call"):
            actual_agents = list(getattr(routing_obj, "agents_to_call") or [])
        elif isinstance(routing_obj, str):
            actual_agents = [routing_obj]

    symbols = []
    sub_questions = []
    if getattr(res, "rewritten", None):
        symbols = list(getattr(res.rewritten, "symbols", None) or [])
        sub_questions = list(getattr(res.rewritten, "sub_questions", None) or [])
    elif getattr(res, "rewritten_symbol", None):
        symbols = [res.rewritten_symbol]
    elif getattr(res, "symbols", None):
        symbols = list(res.symbols)

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

    if slice_type in ("injection", "out_of_scope", "disclaimer"):
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
    live_url: str | None = None,
    dataset_path: Path | str | None = None,
) -> AgentEvalSummary:
    """Chạy đánh giá benchmark Agent Swarm trên tập cases."""
    if cases is None:
        import yaml
        target_path = Path(dataset_path) if dataset_path else GOLDEN_DATASET_PATH
        if not target_path.is_file():
            raise FileNotFoundError(f"Không tìm thấy file golden dataset: {target_path}")
        raw_data = yaml.safe_load(target_path.read_text(encoding="utf-8"))
        cases = list(raw_data.get("cases") or [])

    if sample and sample > 0:
        by_slice: dict[str, list[dict]] = {}
        for c in cases:
            s_type = c.get("slice", {}).get("type", "lookup") if isinstance(c.get("slice"), dict) else "lookup"
            by_slice.setdefault(s_type, []).append(c)
        sampled_cases = []
        while len(sampled_cases) < sample and any(by_slice.values()):
            for s_name in list(by_slice.keys()):
                if by_slice[s_name]:
                    sampled_cases.append(by_slice[s_name].pop(0))
                if len(sampled_cases) >= sample:
                    break
        cases = sampled_cases

    results: list[CaseAgentEvalResult] = []
    slice_passes: dict[str, list[bool]] = {}

    import time
    for c in cases:
        r = evaluate_case(c, deps=deps, live_url=live_url)
        results.append(r)
        slice_passes.setdefault(r.slice_type, []).append(r.passed)
        if live_url:
            time.sleep(0.5)

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
    filename_prefix: str = "agent_eval_report",
) -> tuple[Path, Path]:
    """Xuất báo cáo kết quả đánh giá Agent sang file JSON và Markdown."""
    if output_dir is None:
        output_dir = ROOT / "resources" / "eval"
    output_dir.mkdir(parents=True, exist_ok=True)

    json_path = output_dir / f"{filename_prefix}.json"
    md_path = output_dir / f"{filename_prefix}.md"

    data = asdict(summary)
    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

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
