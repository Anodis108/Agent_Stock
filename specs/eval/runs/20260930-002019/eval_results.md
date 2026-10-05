# Báo Cáo Đánh Giá Chất Lượng Agent: golden_v5.yaml

- **Thời gian chạy**: `2026-09-30 00:20:34`
- **Model chính**: `gpt-4o-mini` | **LLM Judge**: `gpt-4o-mini`
- **Tổng số ca kiểm thử**: **1**
- **Kết quả**: **0/1 Passed (0.0%)**
- **Tổng Token tiêu thụ**: **2,753 tokens** (Pipeline: 2,104, Judge: 649)
- **Tổng chi phí ước tính**: **$0.0005 USD** (~ **12 VNĐ**)
- **Tổng thời gian thực thi**: **15.5s** (Trung bình: **15.48s/case**)

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
| 1 | `lookup_08` | `lookup` | Giá đóng cửa gần nhất của VNM | `pre_rewrite_guardrail ➔ rewrite_question ➔ supervisor ➔ price_agent ➔ answer_composer` | 2,104 / 649 | 12đ | ❌ **FAIL** | Judge: 1.7/5 (Câu trả lời không chính xác vì giá đóng cửa của cổ phiếu VNM...) |

---

## 3. Bảng Phân Tích Câu Hỏi & Câu Trả Lời Chi Tiết

### ❌ Case [lookup_08] - lookup
- **Câu hỏi**: Giá đóng cửa gần nhất của VNM
- **Expected**: Trả lời có mã VNM và giá hoặc trạng thái dữ liệu.
- **Pipeline Trace**: `pre_rewrite_guardrail ➔ rewrite_question ➔ supervisor ➔ price_agent ➔ answer_composer`
- **Token & Chi phí**: 2753 tokens (2104 app + 649 judge) | **12 VNĐ** ($0.00048)
- **Thời gian phản hồi**: 15.48s
- **Câu trả lời thực tế**:
```text
Giá đóng cửa gần nhất của cổ phiếu VNM là 60.3.
```
- **Lý do không đạt**:
  - Rule-based: Missing=[], Forbidden=[]
  - LLM-Judge: {"correctness": 1, "completeness": 3, "grounding": 1, "overall": 1.6666666666666667, "reasoning": "Câu trả lời không chính xác vì giá đóng cửa của cổ phiếu VNM không phải là 60.3. Thông tin không được xác thực và không có căn cứ rõ ràng."}
