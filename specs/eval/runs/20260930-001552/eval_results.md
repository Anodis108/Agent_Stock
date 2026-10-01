# Báo Cáo Đánh Giá Chất Lượng Agent: golden_v5.yaml

- **Thời gian chạy**: `2026-09-30 00:16:13`
- **Model chính**: `gpt-4o-mini` | **LLM Judge**: `gpt-4o-mini`
- **Tổng số ca kiểm thử**: **1**
- **Kết quả**: **0/1 Passed (0.0%)**
- **Tổng Token tiêu thụ**: **2,607 tokens** (Pipeline: 1,929, Judge: 678)
- **Tổng chi phí ước tính**: **$0.0005 USD** (~ **12 VNĐ**)
- **Tổng thời gian thực thi**: **21.2s** (Trung bình: **21.24s/case**)

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
| 1 | `lookup_08` | `lookup` | Giá đóng cửa gần nhất của VNM | `pre_rewrite_guardrail ➔ rewrite_question ➔ supervisor ➔ price_agent ➔ answer_composer` | 1,929 / 678 | 12đ | ❌ **FAIL** | Judge: 1.3/5 (Câu trả lời cung cấp thông tin về giá đóng cửa của cổ phiếu ...) |

---

## 3. Bảng Phân Tích Câu Hỏi & Câu Trả Lời Chi Tiết

### ❌ Case [lookup_08] - lookup
- **Câu hỏi**: Giá đóng cửa gần nhất của VNM
- **Expected**: Trả lời có VNM và giá đóng cửa theo dữ liệu thị trường hoặc trạng thái dữ liệu.
- **Pipeline Trace**: `pre_rewrite_guardrail ➔ rewrite_question ➔ supervisor ➔ price_agent ➔ answer_composer`
- **Token & Chi phí**: 2607 tokens (1929 app + 678 judge) | **12 VNĐ** ($0.00047)
- **Thời gian phản hồi**: 21.24s
- **Câu trả lời thực tế**:
```text
Giá đóng cửa gần nhất của cổ phiếu VNM là 60.3, không đổi so với phiên trước.
```
- **Lý do không đạt**:
  - Rule-based: Missing=[], Forbidden=[]
  - LLM-Judge: {"correctness": 1, "completeness": 2, "grounding": 1, "overall": 1.3333333333333333, "reasoning": "Câu trả lời cung cấp thông tin về giá đóng cửa của cổ phiếu VNM, nhưng giá trị 60.3 không có căn cứ và không thể xác nhận tính chính xác của nó. Thông tin không được cập nhật và không phản ánh dữ liệu thực tế."}
