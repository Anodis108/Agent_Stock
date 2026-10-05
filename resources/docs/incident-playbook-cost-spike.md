# Incident Playbook: Cost Spike

## 1. Detection
- **Alert:** Cảnh báo từ `cost_dashboard` hoặc system metrics về việc chi phí USD/VND tăng vọt bất thường.
- **Dấu hiệu:** `Total Cost` tăng > 300% so với ngày trước, hoặc `requests` tăng bất thường.

## 2. Triage
- Chạy lệnh: `PYTHONPATH=src python scripts/cost_dashboard.py` để xem chi tiết.
- Kiểm tra `cache_hit_rate`. Nếu quá thấp (< 20%), có thể cache đang không hoạt động (semantic cache threshold quá cao, hoặc exact cache bị bypass).
- Kiểm tra `by_feature` trong JSON output để xem agent/feature nào đang tiêu tốn nhiều token nhất (ví dụ: `supervisor` bị kẹt trong vòng lặp vô hạn).

## 3. Actions
1. **Kiểm tra Cache:**
   - Đảm bảo Redis/Semantic Cache vẫn đang chạy bình thường.
   - Giảm độ nhạy của semantic cache nếu cần.
2. **Rate Limit:**
   - Áp dụng hoặc thắt chặt rate limit theo IP hoặc User-ID để giảm số lượng requests.
3. **Model Downgrade (nếu khẩn cấp):**
   - Chuyển `settings.llm_model` từ `gpt-4o` sang `gpt-4o-mini` để giảm chi phí 15-20 lần.
4. **Fix Bug:**
   - Nếu do agent lặp vô hạn (infinite loop trong LangGraph), deploy hotfix để thêm `recursion_limit` hoặc sửa logic guardrail.

## 4. Escalation
- Báo cáo cho Technical Lead hoặc Project Manager nếu không thể kiểm soát chi phí.
- Tạm khóa hệ thống nếu chi phí vượt mức ngân sách khẩn cấp.
