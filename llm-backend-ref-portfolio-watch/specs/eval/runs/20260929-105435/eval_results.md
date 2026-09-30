# Báo Cáo Đánh Giá Chất Lượng Agent: golden_v5.yaml

- **Thời gian chạy**: `2026-09-29 10:55:08`
- **Model chính**: `gpt-4o-mini` | **LLM Judge**: `gpt-4o-mini`
- **Tổng số ca kiểm thử**: **2**
- **Kết quả**: **2/2 Passed (100.0%)**
- **Tổng Token tiêu thụ**: **3,613 tokens** (Pipeline: 3,613, Judge: 0)
- **Tổng chi phí ước tính**: **$0.0006 USD** (~ **16 VNĐ**)
- **Tổng thời gian thực thi**: **33.6s** (Trung bình: **16.80s/case**)

---

## 1. Tổng Hợp Theo Từng Slice (Phân Nhóm)

| Slice | Số Case | Passed | Failed | Pass Rate |
| :--- | :---: | :---: | :---: | :---: |
| **lookup** | 2 | 2 | 0 | **100.0%** |
| **comparison** | 0 | 0 | 0 | **N/A** |
| **out_of_scope** | 0 | 0 | 0 | **N/A** |
| **injection** | 0 | 0 | 0 | **N/A** |
| **diagram** | 0 | 0 | 0 | **N/A** |

---

## 2. Bảng Chi Tiết Toàn Bộ 2 Test Cases

| STT | Case ID | Slice | Câu Hỏi | Pipeline Trace Agent | Tokens (App/Judge) | Chi Phí (VNĐ) | Kết Quả | Chi Tiết / Lý Do |
| :---: | :--- | :--- | :--- | :--- | :---: | :---: | :---: | :--- |
| 1 | `lookup_01` | `lookup` | Giá FPT hôm nay bao nhiêu? | `pre_rewrite_guardrail ➔ rewrite_question ➔ supervisor ➔ price_agent ➔ answer_composer` | 1,846 / 0 | 8đ | ✅ **PASS** | Tất cả tiêu chí đạt chuẩn |
| 2 | `lookup_02` | `lookup` | Cho tôi giá hiện tại của VNM | `pre_rewrite_guardrail ➔ rewrite_question ➔ supervisor ➔ price_agent ➔ answer_composer` | 1,767 / 0 | 8đ | ✅ **PASS** | Tất cả tiêu chí đạt chuẩn |

---

## 3. Bảng Phân Tích Câu Hỏi & Câu Trả Lời Chi Tiết

### ✅ Case [lookup_01] - lookup
- **Câu hỏi**: Giá FPT hôm nay bao nhiêu?
- **Expected**: Trả lời có mã FPT và thông tin giá (hoặc báo trạng thái dữ liệu).
- **Pipeline Trace**: `pre_rewrite_guardrail ➔ rewrite_question ➔ supervisor ➔ price_agent ➔ answer_composer`
- **Token & Chi phí**: 1846 tokens (1846 app + 0 judge) | **8 VNĐ** ($0.00031)
- **Thời gian phản hồi**: 28.79s
- **Câu trả lời thực tế**:
```text
Giá cổ phiếu FPT hôm nay là 63.5, giảm 0.31% so với phiên trước.
```

### ✅ Case [lookup_02] - lookup
- **Câu hỏi**: Cho tôi giá hiện tại của VNM
- **Expected**: Trả lời có mã VNM và giá hoặc trạng thái dữ liệu.
- **Pipeline Trace**: `pre_rewrite_guardrail ➔ rewrite_question ➔ supervisor ➔ price_agent ➔ answer_composer`
- **Token & Chi phí**: 1767 tokens (1767 app + 0 judge) | **8 VNĐ** ($0.00030)
- **Thời gian phản hồi**: 4.71s
- **Câu trả lời thực tế**:
```text
Giá hiện tại của cổ phiếu VNM là 60.0. Cổ phiếu này đã giảm 0.50% so với giá đóng cửa trước đó là 60.3.
```
