import argparse
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add src to PYTHONPATH if not already there
root_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root_dir / "src"))

from backend.eval.run_detailed import run_detailed_evaluation

def main():
    parser = argparse.ArgumentParser(description="Eval bundle runner: detailed eval + timestamped artifacts")
    parser.add_argument("--limit", type=int, help="Limit number of cases")
    parser.add_argument("--slice", type=str, help="Filter by slice")
    parser.add_argument("--case-id", type=str, help="Filter by case ID")
    parser.add_argument("--skip-judge", action="store_true", help="Skip LLM Judge")
    parser.add_argument("--skip-agent-eval", action="store_true", help="Skip agent evaluation")
    parser.add_argument("--delay", type=float, default=0.5, help="Delay between cases")

    args = parser.parse_args()

    # Generate timestamp for this run
    now = datetime.now()
    ts_str = now.strftime("%Y%m%d-%H%M%S")
    
    # Setup directories
    specs_eval_dir = root_dir / "specs" / "eval"
    run_dir = specs_eval_dir / "runs" / ts_str
    run_dir.mkdir(parents=True, exist_ok=True)
    
    timestamped_md_path = run_dir / "eval_results.md"
    timestamped_json_path = run_dir / "eval_results.json"
    summary_path = run_dir / "summary.json"
    
    # Latest symlink paths (or copies)
    latest_md_path = specs_eval_dir / "eval_results_golden_v5.md"
    latest_json_path = specs_eval_dir / "eval_results_golden_v5.json"

    print(f"--- Starting Golden V5 Eval Bundle Run: {ts_str} ---")

    # Run the evaluation
    detailed_results, json_payload = run_detailed_evaluation(
        dataset_path=None, # use default golden_v5
        output_md_path=timestamped_md_path,
        output_json_path=timestamped_json_path,
        case_delay_sec=args.delay,
        limit=args.limit,
        slice_filter=args.slice,
        case_id_filter=args.case_id,
        skip_judge=args.skip_judge,
        skip_agent_eval=args.skip_agent_eval,
        save_baseline=False,
    )

    # Write summary.json
    if json_payload and "summary" in json_payload:
        summary_data = {
            "run_id": ts_str,
            "timestamp": json_payload.get("timestamp"),
            "dataset": json_payload.get("dataset"),
            "total_cases": json_payload["summary"].get("total_cases"),
            "passed": json_payload["summary"].get("passed_cases"),
            "failed": json_payload["summary"].get("failed_cases"),
            "pass_rate": json_payload["summary"].get("pass_rate_pct"),
            "slice_breakdown": json_payload["summary"].get("by_slice"),
        }
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary_data, f, ensure_ascii=False, indent=2)

    # Update latest pointers
    if timestamped_md_path.exists():
        shutil.copy2(timestamped_md_path, latest_md_path)
    if timestamped_json_path.exists():
        shutil.copy2(timestamped_json_path, latest_json_path)

    print("\n--- Eval Bundle Run Completed ---")
    print(f"Timestamped results directory: {run_dir}")
    print(f"Summary JSON: {summary_path}")
    print(f"Latest MD: {latest_md_path}")
    print(f"Latest JSON: {latest_json_path}")

if __name__ == "__main__":
    main()
