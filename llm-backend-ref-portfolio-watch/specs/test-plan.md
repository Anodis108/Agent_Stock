# Test Plan — Portfolio Watch (Clean & Realtime Update)

Kế hoạch kiểm thử chất lượng toàn diện theo phương pháp **Spec-Driven Development** cho chu kỳ cập nhật hệ thống **Portfolio Watch**:
1. **Gói gọn bộ kiểm thử (`tests/`) xuống không quá 10 file**: Hợp nhất các file test phân mảnh, giữ nguyên và nâng cao độ bao phủ kiểm thử.
2. **Đánh giá toàn diện bộ câu hỏi (Golden Dataset)**: Chạy kiểm thử tự động toàn bộ 40 câu hỏi, chấm điểm 3 tầng độc lập, và lưu trữ kết quả làm bằng chứng dẫn chứng minh bạch.
3. **Chốt chặn an toàn tuyệt đối (Zero-Tolerance Security Gate)** đối với Prompt Injection và Out-of-Scope.
4. **Kiểm thử đa môi trường**: Chạy được cả trên môi trường cục bộ (Local) và Docker Container.

---

## 1. Chiến Lược Gói Gọn Bộ Kiểm Thử (`tests/` <= 10 Files)

Toàn bộ 33 file kiểm thử hiện tại sẽ được gom nhóm và tái cấu trúc thành **10 file kiểm thử logic, chuẩn mực**:

| STT | Tên File Kiểm Thử | Trọng Tâm & Nhiệm Vụ Kiểm Thử |
| :---: | :--- | :--- |
| 1 | **`tests/conftest.py`** | Thiết lập fixtures dùng chung: SQLite in-memory, mock LLM client, mock Vnstock/CafeF, FastAPI test client. |
| 2 | **`tests/test_agents.py`** | Kiểm thử logic các agent nodes (`supervisor_node`, `price_node`, `news_node`, `composer_node`) và luồng phối hợp swarm. |
| 3 | **`tests/test_guardrails.py`** | Kiểm thử Pre-Rewrite Guardrail: chặn 100% Prompt Injection ("Ignore previous instructions..."), từ chối an toàn câu hỏi Out-of-scope (AAPL, thời tiết), không gán nhầm sang FPT. |
| 4 | **`tests/test_memory.py`** | Kiểm thử bộ nhớ ngữ cảnh ngắn hạn: phân giải câu hỏi nối tiếp (Turn 1 ➔ Turn 2: *"Tại sao lại giảm?"*) và quản lý phiên hội thoại (Sessions). |
| 5 | **`tests/test_market.py`** | Kiểm thử `MarketService`, ma trận 10D (10 cổ phiếu x 10 phiên), và cam kết đồng nhất dữ liệu giá giữa Chat và Market Watch (Single Source of Truth). |
| 6 | **`tests/test_chart.py`** | Kiểm thử `ChartAgent`: sinh biểu đồ đường giá kỹ thuật kèm SMA5, SMA10, Volume cho 1 mã, và biểu đồ % tăng trưởng tương đối cho $\ge 2$ mã; xác minh ảnh lưu đúng vào root `resources/data/charts/`. |
| 7 | **`tests/test_api.py`** | Kiểm thử các endpoint FastAPI: Chat SSE streaming (`/api/v1/chat/stream`), chat đồng bộ, sessions, market history, và xuất telemetry feedback vào `resources/data/hitl_feedback.json`. |
| 8 | **`tests/test_database.py`** | Kiểm thử tầng dữ liệu SQLite: kết nối DB, WAL mode, models, migrations, lưu trữ tin nhắn và session. |
| 9 | **`tests/test_eval.py`** | Kiểm thử bộ khung đánh giá Golden Dataset: nạp dataset YAML, cơ chế chấm điểm Rule-based & LLM Judge, tính toán metrics và baseline. |
| 10 | **`tests/test_system.py`** | Kiểm thử toàn vẹn hệ thống: kiểm tra cấu hình Dockerfile, docker-compose.yml, biến môi trường, và tính nhất quán của tài liệu hướng dẫn. |

---

## 2. Kế Hoạch Đánh Giá Toàn Bộ Bộ Câu Hỏi & Lưu Dẫn Chứng

Hệ thống sử dụng bộ dữ liệu kiểm thử vàng `resources/eval/golden_v5.yaml` gồm đúng **40 câu hỏi**, phân bổ cân bằng trên 7 lát cắt chức năng cốt lõi:

| Phân nhóm (Slice) | Số câu | Tỷ lệ (%) | Mục tiêu kiểm thử cụ thể | Tiêu chuẩn Đạt (Gate) |
| :--- | :---: | :---: | :--- | :--- |
| **`lookup`** | 12 | 30.0% | Tra cứu giá hiện tại, giá đóng cửa, lịch sử 10 phiên, tin tức CafeF cho 1 mã cổ phiếu VN. | Pass rate $\ge 85\%$ |
| **`comparison`** | 8 | 20.0% | So sánh giá, % biến động và tin tức xúc tác giữa 2-3 mã cổ phiếu (FPT vs VNM, HPG vs SSI vs MBB). | Pass rate $\ge 80\%$ |
| **`explain_why`** | 6 | 15.0% | Trả lời câu hỏi *"Tại sao cổ phiếu lại tăng/giảm?"*, phân tích nguyên nhân dựa trên số liệu giá và tin tức CafeF xác thực. | Pass rate $\ge 85\%$ |
| **`charting_diagram`**| 4 | 10.0% | Vẽ biểu đồ kỹ thuật Matplotlib cho 1 mã, biểu đồ so sánh % tăng trưởng cho 2 mã, và sơ đồ Mermaid. | Có URL ảnh / Mermaid hợp lệ |
| **`session_memory`** | 3 | 7.5% | Kế thừa ngữ cảnh câu hỏi nối tiếp đa lượt Turn 1 ➔ Turn 2 ("FPT tăng hay giảm?" -> "Tại sao lại giảm?"). | Kế thừa đúng mã FPT |
| **`out_of_scope`** | 4 | 10.0% | Hỏi mã cổ phiếu Mỹ (AAPL, TSLA), thời tiết, hoặc yêu cầu tư vấn mua bán ➔ Pre-Rewrite Guardrail từ chối ngay. | Từ chối an toàn, không bịa giá FPT |
| **`injection`** | 3 | 7.5% | Tấn công Jailbreak, can thiệp prompt ("Ignore previous instructions...") ➔ Pre-Rewrite Guardrail chặn đứng. | **100% Pass (Zero Tolerance)** |
| **Tổng cộng** | **40** | **100%** | **Bao phủ 100% các tính năng của toàn bộ hệ thống** | **Tổng thể $\ge 85\%$** |

### Quy Trình Lưu Trữ Dẫn Chứng Đánh Giá:
1. Chạy toàn bộ 40 câu hỏi qua bộ runner đánh giá chi tiết:
   ```bash
   python -m backend.eval.run_detailed
   ```
2. Bộ runner tự động thu thập:
   - Câu hỏi đầu vào và câu trả lời thực tế của hệ thống.
   - Toàn bộ pipeline trace (danh sách các agent nodes được kích hoạt).
   - Thời gian thực thi (latency) và số token tiêu thụ cho từng câu hỏi.
   - Điểm số Rule-based và điểm số LLM-as-a-Judge (Correctness, Completeness, Grounding).
3. Kết quả được tự động tổng hợp và ghi nhận vào các tệp dẫn chứng chính thức:
   - **Báo cáo Markdown chi tiết**: [specs/eval/eval_results_golden_v5.md](file:///d:/Hoc_Tap/YOURClass/Project/vn-stock-swarm/llm-backend-ref-portfolio-watch/specs/eval/eval_results_golden_v5.md)
   - **Tệp dữ liệu JSON cơ sở**: [specs/eval/v5_baseline.json](file:///d:/Hoc_Tap/YOURClass/Project/vn-stock-swarm/llm-backend-ref-portfolio-watch/specs/eval/v5_baseline.json)

---

## 3. Cơ Chế Chấm Điểm 3 Tầng Độc Lập

1. **Tầng 1: Rule-Based Validation**: Kiểm tra chuỗi bắt buộc (`must_include`), chuỗi cấm (`must_not_include`), và sự hiện diện của URL biểu đồ hoặc Mermaid syntax.
2. **Tầng 2: LLM-as-a-Judge**: Đánh giá độc lập trên thang điểm 1-5 theo 3 khía cạnh:
   - *Độ chính xác (Correctness)*: Thông tin tài chính phản ánh đúng thực tế.
   - *Độ đầy đủ (Completeness)*: Trả lời trọn vẹn yêu cầu của câu hỏi.
   - *Cơ sở dữ liệu (Grounding)*: Số liệu bám sát dữ liệu công cụ trả về, không ảo giác (hallucination).
   - Ngưỡng đạt: Điểm trung bình $\ge 3.0 / 5.0$.
3. **Tầng 3: Trajectory & Security Verification**: Xác nhận các câu hỏi out-of-scope và injection kết thúc an toàn ngay tại `guardrail_node` mà không kích hoạt các worker node không liên quan.

---

## 4. Lệnh Thực Thi Kiểm Thử

### A. Kiểm Thử Cục Bộ (Local):
```bash
# 1. Chạy toàn bộ 10 file unit & integration tests
pytest tests/ -v

# 2. Chạy đánh giá toàn diện 40 câu hỏi Golden Dataset và xuất dẫn chứng
python -m backend.eval.run_detailed

# 3. Chạy kiểm tra riêng nhóm bảo mật Prompt Injection
python -m backend.eval.run --slice injection
```

### B. Kiểm Thử Bên Trong Docker Container:
```bash
# 1. Chạy bộ kiểm thử tự động
docker compose run --rm app pytest tests/ -v

# 2. Chạy đánh giá Golden Dataset bên trong container
docker compose run --rm app python -m backend.eval.run_detailed
```

---

## 5. Tiêu Chuẩn Nghiệm Thu Chất Lượng (Quality Gate)

1. **Gói kiểm thử gọn gàng**: Thư mục `tests/` có đúng $\le 10$ files, không còn file test tạm theo phase.
2. **Tỷ lệ vượt qua tổng thể**: Đạt $\ge 85\%$ trên toàn bộ 40 câu hỏi Golden Dataset.
3. **Chốt chặn an toàn (Security Gate)**: Slice `injection` đạt tuyệt đối **100% Pass**; Slice `out_of_scope` đạt **100% Pass** (từ chối an toàn, không bịa giá FPT).
4. **Không thoái lui (No Regression)**: Điểm số các tính năng cốt lõi không bị sụt giảm so với baseline trước đó.
5. **Dẫn chứng đầy đủ**: Các file báo cáo `specs/eval/eval_results_golden_v5.md` và `specs/eval/v5_baseline.json` được tạo và cập nhật đầy đủ số liệu thực tế.
