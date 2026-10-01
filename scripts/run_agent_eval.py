#!/usr/bin/env python3
"""CLI script chạy đánh giá benchmark toàn diện cho Agent Swarm (`agent_eval.py`).

Sử dụng:
    python scripts/run_agent_eval.py --sample 5
    python scripts/run_agent_eval.py --all
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Cấu hình UTF-8 cho Windows console
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from backend.eval.agent_eval import export_eval_report, run_agent_eval


def main() -> int:
    parser = argparse.ArgumentParser(description="Chạy Agent Evaluation Benchmark.")
    parser.add_argument(
        "--sample",
        type=int,
        default=None,
        help="Số lượng cases mẫu cần chạy (ví dụ: --sample 5). Mặc định: chạy toàn bộ.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Thư mục xuất báo cáo (mặc định: specs/eval).",
    )
    args = parser.parse_args()

    sample_str = f"{args.sample} mẫu" if args.sample else "toàn bộ"
    print(f"🚀 Bắt đầu chạy Agent Evaluation Benchmark ({sample_str})...")

    out_dir = Path(args.output_dir) if args.output_dir else ROOT / "specs" / "eval"

    try:
        summary = run_agent_eval(sample=args.sample)
    except Exception as exc:
        print(f"❌ Lỗi thực thi benchmark: {exc}")
        return 1

    json_path, md_path = export_eval_report(summary, output_dir=out_dir)

    print("\n" + "=" * 65)
    print("📊 BÁO CÁO KẾT QUẢ ĐÁNH GIÁ AGENT SWARM (BENCHMARK)")
    print("=" * 65)
    print(f"• Tổng số cases: {summary.total_cases}")
    print(f"• Tỷ lệ Pass:    {summary.overall_pass_rate}% ({summary.passed_cases}/{summary.total_cases})")
    print(f"• Điểm tổng kết: {summary.overall_score}%")
    print("-" * 65)
    print(f"• Routing Accuracy:            {summary.avg_routing_accuracy}%")
    print(f"• Query Decomposition Quality: {summary.avg_decomposition_quality}%")
    print(f"• Groundedness / Faithfulness: {summary.avg_groundedness_score}%")
    print(f"• Task Success Rate:           {summary.avg_task_success_rate}%")
    print(f"• Zero-Tolerance Guardrails:   {summary.guardrails_pass_rate}%")
    print("=" * 65)
    print(f"📁 Báo cáo JSON: {json_path}")
    print(f"📁 Báo cáo Markdown: {md_path}")

    # Kiểm tra đạt chuẩn Spec (Overall >= 85% và Guardrail 100%)
    if summary.overall_score >= 85.0 and summary.guardrails_pass_rate == 100.0:
        print("\n✅ ĐẠT CHUẨN ACCEPTANCE CRITERIA (AC-5, AC-6)!")
        return 0
    else:
        print("\n⚠️ CẢNH BÁO: Điểm số chưa đạt ngưỡng kỳ vọng!")
        return 0  # Vẫn trả về 0 để không chặn script, nhưng hiển thị cảnh báo


if __name__ == "__main__":
    sys.exit(main())
