# Báo Cáo Đánh Giá Swarm Agent (`agent_eval.py`)

- **Thời gian thực thi:** `2026-10-05T15:30:51.814411+00:00`
- **Tổng số test cases:** `2`
- **Tỷ lệ Pass tổng thể:** `100.0%` (2/2)
- **Điểm tổng kết (Overall Score):** `100.0%`

## 1. Bảng Chỉ Số Đánh Giá Cốt Lõi (Core Metrics)

| Chỉ Số Đánh Giá | Kết Quả Đạt Được | Ngưỡng Chuẩn Spec | Trạng Thái |
| :--- | :---: | :---: | :---: |
| **Routing Accuracy** | `100.0%` | $\ge 90\%$ | ✅ PASS |
| **Routing Precision / Recall** | `100.0%` / `100.0%` | $\ge 85\%$ | ✅ PASS |
| **Query Decomposition Quality** | `100.0%` | $\ge 90\%$ | ✅ PASS |
| **Groundedness / Faithfulness** | `100.0%` | $\ge 95\%$ | ✅ PASS |
| **Task Success Rate** | `100.0%` | $\ge 85\%$ | ✅ PASS |
| **Zero-Tolerance Guardrails** | `100.0%` | **100% (Bắt buộc)** | ✅ PASS |

## 2. Kết Quả Theo Từng Nhóm Câu Hỏi (Slices)

| Nhóm Câu Hỏi (Slice) | Tỷ Lệ Đạt Chuẩn (%) |
| :--- | :---: |
| `lookup` | `100.0%` |
| `comparison` | `100.0%` |

## 3. Chi Tiết Từng Ca Kiểm Thử

| ID | Nhóm | Câu Hỏi | Agents | Routing | Decompose | Grounded | Kết Quả |
| :--- | :--- | :--- | :--- | :---: | :---: | :---: | :---: |
| `lookup_01` | `lookup` | Giá FPT hôm nay bao nhiêu? | `price` | 100% | 100% | 100% | ✅ PASS |
| `comparison_01` | `comparison` | So sánh VNM và HPG tuần này | `price+news+eval` | 100% | 100% | 100% | ✅ PASS |