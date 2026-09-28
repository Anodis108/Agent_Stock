#!/usr/bin/env python3
"""So sánh output render prompt v1 vs v2 — M3-B1 Phase 3.

In cạnh nhau 5 câu hỏi stock mẫu cho các prompt có nhiều version
(hiện tại: answer_compose, rewrite_question).
"""

from __future__ import annotations

import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.infra.llm.prompt_registry import registry  # noqa: E402

SEP = "-" * 72

REWRITE_SAMPLES: list[dict[str, object]] = [
    {
        "label": "1. Tra cứu giá trực tiếp",
        "question": "Giá FPT hôm nay bao nhiêu?",
        "conversation": "[]",
    },
    {
        "label": "2. Turn 2 — đại từ không có mã",
        "question": "Tại sao lại giảm?",
        "conversation": '[{"role":"user","content":"Giá FPT hôm nay?"},{"role":"assistant","content":"FPT đóng cửa 95000 VND."}]',
    },
    {
        "label": "3. So sánh hai mã",
        "question": "So sánh FPT và VNM",
        "conversation": "[]",
    },
    {
        "label": "4. Turn 2 — mã đó",
        "question": "Mã đó còn tin gì mới không?",
        "conversation": '[{"role":"user","content":"HPg giá thế nào?"}]',
    },
    {
        "label": "5. Yêu cầu biểu đồ",
        "question": "Vẽ biểu đồ giá HPG 10 ngày",
        "conversation": "[]",
    },
]

ANSWER_SAMPLES: list[dict[str, object]] = [
    {
        "label": "A1. Lookup FPT có giá",
        "question": "Giá FPT?",
        "symbol": "FPT",
        "price_summary": "FPT: 95000 VND (+1.2%)",
        "news_summary": "(không có tin)",
        "eval_summary": "(không)",
        "evidence": "FPT close=95000 change_pct=1.2",
        "violations": "(không)",
    },
    {
        "label": "A2. Turn 2 explain thiếu tin",
        "question": "Tại sao FPT giảm?",
        "symbol": "FPT",
        "price_summary": "FPT: 93000 VND (-2.1%)",
        "news_summary": "Tin: FPT công bố báo cáo quý",
        "eval_summary": "Biến động tiêu cực",
        "evidence": "FPT close=93000; news_title=FPT công bố báo cáo quý",
        "violations": "(không)",
    },
]


def _print_pair(title: str, v1: str, v2: str) -> None:
    print(f"\n{SEP}\n{title}\n{SEP}")
    print("[v1]")
    print(v1.strip())
    print("\n[v2]")
    print(v2.strip())
    print()


def compare_rewrite() -> None:
    reg = registry()
    print("=== rewrite_question: v1 vs v2 ===")
    for sample in REWRITE_SAMPLES:
        label = str(sample["label"])
        kwargs = {
            "question": sample["question"],
            "conversation": sample["conversation"],
        }
        v1 = reg.render("rewrite_question", version=1, **kwargs)
        v2 = reg.render("rewrite_question", version=2, **kwargs)
        _print_pair(label, v1, v2)


def compare_answer_compose() -> None:
    reg = registry()
    print("=== answer_compose: v1 vs v2 ===")
    for sample in ANSWER_SAMPLES:
        label = str(sample["label"])
        kwargs = {k: v for k, v in sample.items() if k != "label"}
        v1 = reg.render("answer_compose", version=1, **kwargs)
        v2 = reg.render("answer_compose", version=2, **kwargs)
        _print_pair(label, v1, v2)


def main() -> int:
    compare_rewrite()
    compare_answer_compose()
    print("Done — 5 rewrite + 2 answer samples rendered (v1 vs v2).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
