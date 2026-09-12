"""So sánh output giữa 2 version của 1 prompt trong registry (Bài 6, Bước 3).

Chạy CÙNG bộ câu hỏi mẫu qua `version=1` rồi `version=2` của prompt
`supervisor_routing`, in kết quả cạnh nhau — cách kiểm tra nhanh "v2 có đổi
hành vi như kỳ vọng không" trước khi đổi `production.txt` hoặc bật A/B test
thật (AGENT_PR_AB_TREATMENT_PCT).

Dùng:
    python -m app.agent_pr.scripts.compare_prompt_versions
    python -m app.agent_pr.scripts.compare_prompt_versions --prompt supervisor_routing --v1 1 --v2 2
"""

from __future__ import annotations

import argparse

from app.agent_pr.prompt_registry import registry
from app.agent_pr.supervisor_agent.schemas import RoutingDecision
from app.guardrails.injection import bound_messages
from app.llm.completion import chat_parsed
from app.llm.params import DETERMINISTIC

# 5 tình huống mẫu — cùng dữ liệu `context.py`/checklist Bước 3, thay bằng
# domain của agent_pr (routing) thay vì Q&A pháp lý trong slide gốc.
_SAMPLE_TASKS = [
    {
        "question": "Giá HPG hôm nay tăng hay giảm?",
        "symbols": "HPG",
        "notes": "(chưa có)",
    },
    {
        "question": "Tại sao FPT tăng giá hôm nay?",
        "symbols": "FPT",
        "notes": "[FPT][price_agent] Giá 135.000, +2.3% so phiên trước\n"
        "[FPT][news_agent] 3 tin: 'FPT ký hợp đồng lớn với đối tác Nhật'",
    },
    {
        "question": "So sánh HPG và VNM hôm nay",
        "symbols": "HPG, VNM",
        "notes": "[HPG][price_agent] Giá 28.500, +1.1%",
    },
    {
        "question": "Lưu lại dữ liệu HPG vừa lấy vào kho",
        "symbols": "HPG",
        "notes": "[HPG][price_agent] Giá 28.500, +1.1% (mới crawl)\n"
        "[HPG][db_write] Đã soạn lệnh lưu giá HPG, chờ duyệt.",
    },
    {
        "question": "Vừa rồi tôi hỏi mã nào?",
        "symbols": "(chưa rõ)",
        "notes": "(chưa có)",
    },
]


def _route_once(prompt_name: str, version: int, task: dict, freshness_minutes: int) -> RoutingDecision:
    system = registry().render(
        prompt_name, version=version, freshness_minutes=str(freshness_minutes)
    )
    user = (
        f"Nhiệm vụ: {task['question']}\n"
        f"Các mã cần xử lý: {task['symbols']}\n"
        f"Ghi chú từ worker đã chạy lượt này:\n{task['notes']}"
    )
    return chat_parsed(bound_messages(system, user), RoutingDecision, DETERMINISTIC)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prompt", default="supervisor_routing")
    parser.add_argument("--v1", type=int, default=1)
    parser.add_argument("--v2", type=int, default=2)
    parser.add_argument("--freshness-minutes", type=int, default=20)
    args = parser.parse_args()

    for i, task in enumerate(_SAMPLE_TASKS, start=1):
        print(f"\n=== Câu {i}: {task['question']} ===")
        try:
            d1 = _route_once(args.prompt, args.v1, task, args.freshness_minutes)
            print(f"  v{args.v1}: next_agent={d1.next_agent!r} symbol={d1.symbol!r} reasoning={d1.reasoning!r}")
        except Exception as exc:
            print(f"  v{args.v1}: LỖI {exc}")
        try:
            d2 = _route_once(args.prompt, args.v2, task, args.freshness_minutes)
            print(f"  v{args.v2}: next_agent={d2.next_agent!r} symbol={d2.symbol!r} reasoning={d2.reasoning!r}")
        except Exception as exc:
            print(f"  v{args.v2}: LỖI {exc}")


if __name__ == "__main__":
    main()
