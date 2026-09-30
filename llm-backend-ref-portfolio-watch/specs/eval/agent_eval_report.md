# Báo Cáo Đánh Giá Swarm Agent (`agent_eval.py`)

- **Thời gian thực thi:** `2026-09-30T09:17:34.799846+00:00`
- **Tổng số test cases:** `5`
- **Tỷ lệ Pass tổng thể:** `80.0%` (4/5)
- **Điểm tổng kết (Overall Score):** `96.2%`

## 1. Bảng Chỉ Số Đánh Giá Cốt Lõi (Core Metrics)

| Chỉ Số Đánh Giá | Kết Quả Đạt Được | Ngưỡng Chuẩn Spec | Trạng Thái |
| :--- | :---: | :---: | :---: |
| **Routing Accuracy** | `100.0%` | $\ge 90\%$ | ✅ PASS |
| **Routing Precision / Recall** | `80.0%` / `100.0%` | $\ge 85\%$ | ✅ PASS |
| **Query Decomposition Quality** | `96.0%` | $\ge 90\%$ | ✅ PASS |
| **Groundedness / Faithfulness** | `100.0%` | $\ge 95\%$ | ✅ PASS |
| **Task Success Rate** | `90.0%` | $\ge 85\%$ | ✅ PASS |
| **Zero-Tolerance Guardrails** | `100.0%` | **100% (Bắt buộc)** | ✅ PASS |

## 2. Kết Quả Theo Từng Nhóm Câu Hỏi (Slices)

| Nhóm Câu Hỏi (Slice) | Tỷ Lệ Đạt Chuẩn (%) |
| :--- | :---: |
| `lookup` | `100.0%` |
| `comparison` | `0.0%` |
| `explain_why` | `100.0%` |
| `charting_diagram` | `100.0%` |
| `session_memory` | `100.0%` |

## 3. Chi Tiết Từng Ca Kiểm Thử

| ID | Nhóm | Câu Hỏi | Agents | Routing | Decompose | Grounded | Kết Quả |
| :--- | :--- | :--- | :--- | :---: | :---: | :---: | :---: |
| `lookup_01` | `lookup` | Giá FPT hôm nay bao nhiêu? | `price+news` | 100% | 80% | 100% | ✅ PASS |
| `comparison_01` | `comparison` | So sánh VNM và HPG tuần này | `price+news+eval` | 100% | 100% | 100% | ❌ FAIL |
| `explain_why_01` | `explain_why` | Tại sao giá FPT giảm hôm nay? | `price+news+eval` | 100% | 100% | 100% | ✅ PASS |
| `charting_diagram_01` | `charting_diagram` | Vẽ biểu đồ giá cổ phiếu FPT 10 phiê... | `price+chart` | 100% | 100% | 100% | ✅ PASS |
| `session_memory_01` | `session_memory` | Tôi đang quan tâm đến FPT. Cổ phiếu... | `price+news` | 100% | 100% | 100% | ✅ PASS |