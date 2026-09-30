# Báo Cáo Đánh Giá Chất Lượng Agent: golden_v5.yaml

- **Thời gian chạy**: `2026-09-29 10:53:42`
- **Model chính**: `gpt-4o-mini` | **LLM Judge**: `gpt-4o-mini`
- **Tổng số ca kiểm thử**: **1**
- **Kết quả**: **1/1 Passed (100.0%)**
- **Tổng Token tiêu thụ**: **1,752 tokens** (Pipeline: 1,752, Judge: 0)
- **Tổng chi phí ước tính**: **$0.0003 USD** (~ **8 VNĐ**)
- **Tổng thời gian thực thi**: **63.1s** (Trung bình: **63.15s/case**)

---

## 1. Tổng Hợp Theo Từng Slice (Phân Nhóm)

| Slice | Số Case | Passed | Failed | Pass Rate |
| :--- | :---: | :---: | :---: | :---: |
| **lookup** | 1 | 1 | 0 | **100.0%** |
| **comparison** | 0 | 0 | 0 | **N/A** |
| **out_of_scope** | 0 | 0 | 0 | **N/A** |
| **injection** | 0 | 0 | 0 | **N/A** |
| **diagram** | 0 | 0 | 0 | **N/A** |

---

## 2. Bảng Chi Tiết Toàn Bộ 1 Test Cases

| STT | Case ID | Slice | Câu Hỏi | Pipeline Trace Agent | Tokens (App/Judge) | Chi Phí (VNĐ) | Kết Quả | Chi Tiết / Lý Do |
| :---: | :--- | :--- | :--- | :--- | :---: | :---: | :---: | :--- |
| 1 | `lookup_01` | `lookup` | Giá FPT hôm nay bao nhiêu? | `pre_rewrite_guardrail ➔ rewrite_question ➔ supervisor ➔ price_agent ➔ answer_composer` | 1,752 / 0 | 8đ | ✅ **PASS** | Tất cả tiêu chí đạt chuẩn |

---

## 3. Bảng Phân Tích Câu Hỏi & Câu Trả Lời Chi Tiết

### ✅ Case [lookup_01] - lookup
- **Câu hỏi**: Giá FPT hôm nay bao nhiêu?
- **Expected**: Trả lời có mã FPT và thông tin giá (hoặc báo trạng thái dữ liệu).
- **Pipeline Trace**: `pre_rewrite_guardrail ➔ rewrite_question ➔ supervisor ➔ price_agent ➔ answer_composer`
- **Token & Chi phí**: 1752 tokens (1752 app + 0 judge) | **8 VNĐ** ($0.00030)
- **Thời gian phản hồi**: 63.15s
- **Câu trả lời thực tế**:
```text
Giá cổ phiếu FPT hôm nay là 63.5, giảm 0.31% so với giá đóng cửa trước đó là 63.7.
```
