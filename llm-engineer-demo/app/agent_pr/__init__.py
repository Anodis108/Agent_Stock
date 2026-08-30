"""Thực hành Hierarchical VN-stock — build từng agent, chưa đủ 5 worker.

Thứ tự slice (khớp Sơ đồ 1 → 3, không theo plan.md LLM-hoá):
  1. craw_agent   — lấy giá 1 mã qua vnstock (đang làm)
  2. price_agent  — đọc quote, tính %, chưa gọi Swarm đầy đủ
  3. coordinator  — hub tối giản, 1 worker
  4. news / eval / db / synthesis — thêm sau khi /pr/price ra số thật
"""
