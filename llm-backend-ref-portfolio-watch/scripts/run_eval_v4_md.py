#!/usr/bin/env python3
"""Run evaluation on golden_v4.yaml and export results to a comprehensive Markdown report table."""

from __future__ import annotations

import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
import yaml

# Set environment paths
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Ensure Langfuse doesn't spam logs if unconfigured
os.environ["MONITORING_ENABLED"] = "false"

from backend.eval.run import (
    load_golden_dataset,
    eval_one_case,
    make_answer_fn,
    build_report,
    check_injection_gate,
)
from backend.shared.settings import settings
settings.monitoring_enabled = False


def format_agent_flow(steps: list[dict]) -> str:
    """Format agent steps into a concise visual workflow string."""
    if not steps:
        return "N/A"
    
    flow_items = []
    for s in steps:
        tool = s.get("tool") or s.get("agent") or "unknown"
        flow_items.append(f"`{tool}`")
    
    return " ➔ ".join(flow_items)


def format_agent_steps_detail(steps: list[dict]) -> str:
    """Format detailed agent trajectory."""
    if not steps:
        return "Không ghi nhận steps"
    lines = []
    for idx, s in enumerate(steps, 1):
        tool = s.get("tool") or "unknown"
        obs = s.get("observation", "")
        # Truncate long observation
        if len(obs) > 150:
            obs = obs[:147] + "..."
        lines.append(f"{idx}. **{tool}**: {obs}")
    return "<br>".join(lines)


def format_judge_eval(judge: any, rule: any) -> str:
    """Format LLM-as-Judge evaluation."""
    if judge.skipped:
        reason = judge.skip_reason or "Skipped"
        rule_status = "✅ Rule Pass" if rule.passed else f"❌ Rule Fail (Missing: {rule.missing}, Forbidden: {rule.forbidden_found})"
        return f"*Bỏ qua LLM Judge* ({reason})<br>• {rule_status}"
    
    if judge.score is None:
        return "N/A"
    
    s = judge.score
    res = f"**Điểm TB: {s.overall:.1f}/5.0** (C:{s.correctness}/5, Comp:{s.completeness}/5, G:{s.grounding}/5)<br>"
    res += f"**Nhận xét:** {s.reasoning}"
    return res


def clean_markdown_cell(text: str) -> str:
    """Escape vertical bars and newlines for markdown table cells."""
    if not text:
        return ""
    # Replace newlines with <br>
    cleaned = text.replace("\r\n", "<br>").replace("\n", "<br>").replace("|", "\\|")
    return cleaned


def run_full_eval():
    dataset_path = ROOT / "resources" / "eval" / "golden_v4.yaml"
    print(f"Loading golden dataset from: {dataset_path}")
    raw_data = yaml.safe_load(dataset_path.read_text(encoding="utf-8"))
    cases = raw_data.get("cases", [])
    print(f"Total test cases: {len(cases)}")
    
    results = []
    start_time = time.time()
    
    for i, case in enumerate(cases, 1):
        cid = case.get("id")
        q = case.get("question")
        slice_type = (case.get("slice") or {}).get("type")
        print(f"[{i:02d}/{len(cases):02d}] Running case {cid} ({slice_type})... ", end="", flush=True)
        
        answer_fn = make_answer_fn(user_id=f"eval-v4-{cid}")
        case_res = eval_one_case(
            case,
            answer_fn=answer_fn,
            skip_judge=False,
            skip_agent_eval=False,
        )
        results.append(case_res)
        status_str = "✅ PASS" if case_res.passed else "❌ FAIL"
        print(f"{status_str}")
        
        # Short pause between cases to avoid rate limits
        time.sleep(0.5)

    duration = time.time() - start_time
    report = build_report(results)
    inj_gate = check_injection_gate(results)
    
    print("\n" + "="*50)
    print(f"EVALUATION COMPLETED in {duration:.1f}s")
    print(f"Total: {report.passed}/{report.total} ({report.rate:.1%})")
    print("="*50)

    # Generate Markdown Report
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    
    md = []
    md.append("# 📊 Báo Cáo Đánh Giá Chất Lượng Agent — Golden Dataset v4")
    md.append("")
    md.append(f"- **Thời gian thực thi:** `{now_str}`")
    md.append(f"- **Dataset:** `resources/eval/golden_v4.yaml` (30 cases chuẩn hóa)")
    md.append(f"- **Model:** `{settings.llm_model}`")
    md.append(f"- **Tổng số test cases:** `{report.total}`")
    md.append(f"- **Số case Đạt (Pass):** `{report.passed}` ({report.rate:.1%})")
    md.append(f"- **Số case Thất bại (Fail):** `{report.failed}`")
    md.append(f"- **Injection Gate:** `{'✅ PASS 100%' if inj_gate.passed else '❌ FAIL'}` ({inj_gate.message})")
    md.append("")
    
    # Summary Table by Slice
    md.append("## 📈 Thống Kê Theo Phân Lớp (Slice Breakdown)")
    md.append("")
    md.append("| Phân lớp (Slice) | Số lượng | Đạt (Pass) | Thất bại (Fail) | Tỷ lệ Pass | Trạng thái |")
    md.append("|---|---|---|---|---|:---:|")
    for s in report.by_slice:
        if s.total > 0:
            status_emoji = "✅" if s.passed == s.total else ("⚠️" if s.passed > 0 else "❌")
            rate_str = f"{s.rate:.1%}" if s.rate is not None else "N/A"
            md.append(f"| `{s.slice_type}` | {s.total} | {s.passed} | {s.total - s.passed} | {rate_str} | {status_emoji} |")
    md.append("")
    
    # Main Results Table
    md.append("## 📋 Bảng Chi Tiết Kết Quả Kiểm Thử")
    md.append("")
    md.append("| STT | Case ID | Slice | Câu hỏi | Luồng Agent thực hiện | Kết quả phản hồi (System Output) | Đánh giá LLM as Judge | Kết quả |")
    md.append("|:---:|:---|:---|:---|:---|:---|:---|:---:|")
    
    for idx, r in enumerate(results, 1):
        case_id = r.case_id
        slice_type = f"`{r.slice_type}`"
        question = clean_markdown_cell(r.question)
        flow = clean_markdown_cell(format_agent_flow(r.steps))
        output = clean_markdown_cell(r.output)
        judge_eval = clean_markdown_cell(format_judge_eval(r.judge, r.rule))
        status = "**✅ PASS**" if r.passed else "**❌ FAIL**"
        
        md.append(f"| {idx} | `{case_id}` | {slice_type} | {question} | {flow} | {output} | {judge_eval} | {status} |")
        
    md.append("")
    
    # Detailed Breakdown for Any Failures (or Trajectory Insights)
    if report.failures:
        md.append("## ⚠️ Danh Sách Các Case Thất Bại (Failures & Root Cause)")
        md.append("")
        for f in report.failures:
            md.append(f"### ❌ Case `{f.case_id}` ({f.slice_type})")
            md.append(f"- **Câu hỏi:** {f.question}")
            md.append(f"- **Phản hồi:** {f.output}")
            md.append(f"- **Rule Based:** `missing={f.rule.missing}`, `forbidden={f.rule.forbidden_found}`")
            if not f.judge.skipped and f.judge.score:
                md.append(f"- **LLM Judge Score:** {f.judge.score.overall:.1f}/5.0 (C:{f.judge.score.correctness}, Comp:{f.judge.score.completeness}, G:{f.judge.score.grounding})")
                md.append(f"- **LLM Judge Reasoning:** {f.judge.score.reasoning}")
            if f.error:
                md.append(f"- **Lỗi thực thi:** `{f.error}`")
            md.append("")
    else:
        md.append("## 🎉 Toàn bộ 30 test cases đều đạt chuẩn chất lượng (100% PASS)!")
        md.append("")

    content = "\n".join(md)
    
    # Save to files
    out_file1 = ROOT / "eval_results_golden_v4.md"
    out_file2 = ROOT / "specs" / "eval" / "eval_results_golden_v4.md"
    
    out_file1.write_text(content, encoding="utf-8")
    out_file2.parent.mkdir(parents=True, exist_ok=True)
    out_file2.write_text(content, encoding="utf-8")
    
    print(f"\nReport written successfully to:")
    print(f"1. {out_file1}")
    print(f"2. {out_file2}")


if __name__ == "__main__":
    run_full_eval()
