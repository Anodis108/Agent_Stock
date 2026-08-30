"""Thực hành Hierarchical VN-stock — build từng agent, chưa đủ 5 worker.

Thứ tự slice (khớp Sơ đồ 1 → 3, không theo plan.md LLM-hoá):
  1. craw_agent   — lấy giá 1 mã qua vnstock (xong)
  2. news_agent   — lấy tin thô 1 mã qua vnstock (đang làm; chưa sentiment/HITL)
  3. price_agent  — đọc quote, tính %, chưa gọi Swarm đầy đủ
  4. coordinator  — hub tối giản
  5. eval / db / synthesis — sau khi giá + tin ra số thật
"""
