# Báo Cáo Đánh Giá Chất Lượng Agent: golden_v5.yaml

- **Thời gian chạy**: `2026-09-30 00:22:26`
- **Model chính**: `gpt-4o-mini` | **LLM Judge**: `gpt-4o-mini`
- **Tổng số ca kiểm thử**: **1**
- **Kết quả**: **1/1 Passed (100.0%)**
- **Tổng Token tiêu thụ**: **2,865 tokens** (Pipeline: 2,188, Judge: 677)
- **Tổng chi phí ước tính**: **$0.0005 USD** (~ **13 VNĐ**)
- **Tổng thời gian thực thi**: **19.9s** (Trung bình: **19.88s/case**)

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
| 1 | `lookup_08` | `lookup` | Giá đóng cửa gần nhất của VNM | `pre_rewrite_guardrail ➔ rewrite_question ➔ supervisor ➔ price_agent ➔ answer_composer` | 2,188 / 677 | 13đ | ✅ **PASS** | Judge: 3.0/5 (Câu trả lời cung cấp thông tin về giá đóng cửa của cổ phiếu ...) |

---

## 3. Bảng Phân Tích Câu Hỏi & Câu Trả Lời Chi Tiết

### ✅ Case [lookup_08] - lookup
- **Câu hỏi**: Giá đóng cửa gần nhất của VNM
- **Expected**: Có VNM và thông tin giá/biến động.
- **Pipeline Trace**: `pre_rewrite_guardrail ➔ rewrite_question ➔ supervisor ➔ price_agent ➔ answer_composer`
- **Token & Chi phí**: 2865 tokens (2188 app + 677 judge) | **13 VNĐ** ($0.00051)
- **Thời gian phản hồi**: 19.88s
- **Câu trả lời thực tế**:
```text
Giá đóng cửa gần nhất của cổ phiếu VNM là 60.3.
```
