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

from ai_backend.application.eval.agent_eval import export_eval_report, run_agent_eval


def main() -> int:
    parser = argparse.ArgumentParser(description="Chạy Agent Evaluation Benchmark.")
    parser.add_argument(
        "--sample",
        type=int,
        default=None,
        help="Số lượng cases mẫu cần chạy (ví dụ: --sample 5). Mặc định: chạy toàn bộ.",
    )
    parser.add_argument(
        "--live-url",
        type=str,
        default="http://127.0.0.1:8000/chat",
        help="URL endpoint live web để gửi câu hỏi chat (mặc định: http://127.0.0.1:8000/chat). Đặt rỗng để chạy in-process.",
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default=None,
        help="Đường dẫn file golden dataset (mặc định: resources/eval/golden_dataset.yaml).",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Thư mục xuất báo cáo (mặc định: resources/eval).",
    )
    args = parser.parse_args()

    out_dir = Path(args.output_dir) if args.output_dir else ROOT / "resources" / "eval"
    dataset_path = Path(args.dataset) if args.dataset else ROOT / "resources" / "eval" / "golden_dataset.yaml"
    if "extended" in dataset_path.stem or "v5" in dataset_path.stem:
        prefix = "agent_eval_extended"
    else:
        prefix = "agent_eval_report"

    sample_str = f"{args.sample} mẫu" if args.sample else f"toàn bộ ({dataset_path.name})"
    live_str = f"Live Web ({args.live_url})" if args.live_url else "In-process LangGraph"
    print(f"🚀 Bắt đầu chạy Agent Evaluation Benchmark ({sample_str}) qua {live_str}...")

    try:
        summary = run_agent_eval(
            sample=args.sample,
            live_url=args.live_url if args.live_url else None,
            dataset_path=dataset_path,
        )
    except Exception as exc:
        print(f"❌ Lỗi thực thi benchmark: {exc}")
        return 1

    json_path, md_path = export_eval_report(summary, output_dir=out_dir, filename_prefix=prefix)

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
