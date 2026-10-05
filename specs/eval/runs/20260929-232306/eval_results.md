# Báo Cáo Đánh Giá Chất Lượng Agent: golden_v5.yaml

- **Thời gian chạy**: `2026-09-29 23:23:25`
- **Model chính**: `gpt-4o-mini` | **LLM Judge**: `gpt-4o-mini`
- **Tổng số ca kiểm thử**: **1**
- **Kết quả**: **0/1 Passed (0.0%)**
- **Tổng Token tiêu thụ**: **2,543 tokens** (Pipeline: 1,838, Judge: 705)
- **Tổng chi phí ước tính**: **$0.0005 USD** (~ **12 VNĐ**)
- **Tổng thời gian thực thi**: **19.3s** (Trung bình: **19.30s/case**)

---

## 1. Tổng Hợp Theo Từng Slice (Phân Nhóm)

| Slice | Số Case | Passed | Failed | Pass Rate |
| :--- | :---: | :---: | :---: | :---: |
| **lookup** | 1 | 0 | 1 | **0.0%** |
| **comparison** | 0 | 0 | 0 | **N/A** |
| **out_of_scope** | 0 | 0 | 0 | **N/A** |
| **injection** | 0 | 0 | 0 | **N/A** |
| **diagram** | 0 | 0 | 0 | **N/A** |

---

## 2. Bảng Chi Tiết Toàn Bộ 1 Test Cases

| STT | Case ID | Slice | Câu Hỏi | Pipeline Trace Agent | Tokens (App/Judge) | Chi Phí (VNĐ) | Kết Quả | Chi Tiết / Lý Do |
| :---: | :--- | :--- | :--- | :--- | :---: | :---: | :---: | :--- |
| 1 | `lookup_08` | `lookup` | Giá đóng cửa gần nhất của VNM | `pre_rewrite_guardrail ➔ rewrite_question ➔ supervisor ➔ price_agent ➔ answer_composer` | 1,838 / 705 | 12đ | ❌ **FAIL** | Judge: 2.0/5 (Câu trả lời đưa ra giá đóng cửa là 60.3, nhưng không khớp vớ...) |

---

## 3. Bảng Phân Tích Câu Hỏi & Câu Trả Lời Chi Tiết

### ❌ Case [lookup_08] - lookup
- **Câu hỏi**: Giá đóng cửa gần nhất của VNM
- **Expected**: Thông tin giá đóng cửa gần nhất của cổ phiếu VNM (ví dụ mức giá 60.6 hoặc theo dữ liệu thị trường có sẵn).
- **Pipeline Trace**: `pre_rewrite_guardrail ➔ rewrite_question ➔ supervisor ➔ price_agent ➔ answer_composer`
- **Token & Chi phí**: 2543 tokens (1838 app + 705 judge) | **12 VNĐ** ($0.00047)
- **Thời gian phản hồi**: 19.29s
- **Câu trả lời thực tế**:
```text
Giá đóng cửa gần nhất của cổ phiếu VNM là 60.3.
```
- **Lý do không đạt**:
  - Rule-based: Missing=[], Forbidden=[]
  - LLM-Judge: {"correctness": 2, "completeness": 2, "grounding": 2, "overall": 2.0, "reasoning": "Câu trả lời đưa ra giá đóng cửa là 60.3, nhưng không khớp với thông tin tham khảo hoặc dữ liệu thị trường có sẵn. Thông tin không chính xác và thiếu căn cứ để xác nhận giá trị này. Ngoài ra, câu trả lời cũng không cung cấp thêm thông tin nào khác để làm rõ hơn về giá cổ phiếu VNM."}
