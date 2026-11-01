"""Eval pipeline — bề mặt CLI giống llm-engineer-demo `scripts.eval_pipeline_demo`.

Gọi `ai_backend.application.eval.run` (+ `gate` nếu có --json). Không dùng LangSmith.

    python -m scripts.eval_pipeline --subset --report specs/eval/pr_report.md --json specs/eval/pr_report.json
    python -m scripts.eval_pipeline --subset 20 --report pr.md --json pr.json
    python -m scripts.eval_pipeline --report specs/eval/nightly_report.md --json specs/eval/nightly_report.json --save-history
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_backend.application.eval.gate import main as gate_main  # noqa: E402
from ai_backend.application.eval.run import main as run_main  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--subset",
        type=int,
        nargs="?",
        const=0,
        default=None,
        help="PR subset (golden_pr_subset.yaml). Có thể thêm N → --limit N.",
    )
    parser.add_argument("--report", default=None, metavar="PATH")
    parser.add_argument("--json", default=None, metavar="PATH")
    parser.add_argument(
        "--save-history",
        action="store_true",
        help="Lưu history (nightly).",
    )
    parser.add_argument(
        "--skip-agent-eval",
        action="store_true",
        default=True,
        help="Mặc định bật — tiết kiệm LLM trên CI.",
    )
    args = parser.parse_args(argv)

    run_argv: list[str] = ["--skip-agent-eval"] if args.skip_agent_eval else []
    if args.subset is not None:
        run_argv.append("--subset")
        if args.subset > 0:
            run_argv.extend(["--limit", str(args.subset)])
    else:
        run_argv.append("--run")

    if args.report:
        run_argv.extend(["--report", args.report])
    if args.json:
        run_argv.extend(["--json", args.json])
    if args.save_history:
        run_argv.append("--save-history")

    code = run_main(run_argv)
    if code != 0:
        return code
    if args.json:
        return gate_main(["--run", args.json])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
