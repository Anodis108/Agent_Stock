# Test Plan — Portfolio Watch & Chat Agent

Nguyên tắc: mỗi agent test được độc lập với fake port (không gọi LLM/API
thật trong unit test), cộng vài test tích hợp end-to-end cho luồng chính.

## Unit test theo domain agent

### PriceAgent
- Input giá tăng/giảm/đứng yên → tính đúng % thay đổi so với phiên trước.
- `PriceSource` trả lỗi/không có dữ liệu → agent trả kết quả rõ ràng (không
  crash, không trả None mập mờ).

### NewsAgent
- Fake `NewsSource` trả tin không liên quan → NewsAgent lọc bỏ, trả danh
  sách rỗng thay vì giữ tin rác.
- Fake `NewsSource` cần gọi 2 lần mới đủ tin liên quan → xác nhận vòng lặp
  ReAct gọi tool đúng số lần, dừng khi đủ (không lặp vô hạn).

### Event Classifier
- Giá biến động nhỏ + không tin tức bất thường → phân loại "bình thường".
- Giá biến động lớn hoặc tin tức tiêu cực rõ ràng → phân loại "bất thường".

### EvalAgent
- Đủ dữ liệu ngay từ đầu → không gọi `read_price_history`, ra `Severity`
  trực tiếp.
- Dữ liệu mập mờ → có gọi thêm `read_price_history`, `Severity.confidence`
  thấp hơn khi lịch sử giá không ủng hộ kết luận.

### SynthesisAgent + Guardrail
- `Severity` nghiêm trọng → chọn model lớn hơn (model routing) — assert
  đúng model được chọn theo rule.
- Nội dung soạn ra chứa lời khuyên mua/bán chắc chắn (test bằng câu cố định
  chứa "nên mua"/"nên bán") → Guardrail chặn, agent soạn lại (assert số lần
  gọi LLM soạn > 1 khi vi phạm).
- Nội dung soạn ra có số liệu không khớp evidence đầu vào → Guardrail chặn.

### Confidence Gate
- Confidence cao + khớp ngưỡng user → route "gửi thẳng", không tạo bản ghi
  chờ duyệt.
- Confidence thấp hoặc evidence mâu thuẫn → route vào HITL Gate 1, tạo bản
  ghi "chờ duyệt" đúng nội dung.

### HITL Gate 1 / Gate 2
- Approve → trạng thái chuyển "đã gửi" (Gate 1) hoặc watchlist được cập
  nhật (Gate 2).
- Reject → lý do được ghi vào Memory Store; Gate 2 giữ nguyên cấu hình cũ.
- Gate 2 luôn tạo bản ghi chờ duyệt kể cả khi EvalAgent tự tin cao (không có
  đường tắt — khác Gate 1).

### Supervisor / RewriteQuestion (nhánh hỏi-đáp)
- Câu hỏi chỉ cần tra cứu giá → Supervisor chỉ gọi PriceAgent, không gọi
  EvalAgent.
- Câu hỏi yêu cầu so sánh/giải thích ("tại sao giá giảm") → Supervisor gọi
  cả EvalAgent trước khi soạn câu trả lời.
- Câu hỏi tham chiếu hội thoại trước ("còn mã đó thì sao") → RewriteQuestion
  dùng Memory để chuẩn hoá đúng symbol.

### AnswerComposer
- Không đi qua bất kỳ HITL Gate nào (assert trực tiếp, vì đây là điểm dễ
  làm sai khi thêm code sau này).
- Câu trả lời qua Guardrail giống nhánh giám sát (dùng chung module).

## Test tích hợp (end-to-end, có thể mock LLM/API ngoài)

1. **Quét 1 mã bình thường:** `POST /scan` → không tạo alert nào, chỉ có log.
2. **Quét 1 mã bất thường, confidence cao:** `POST /scan` → alert được gửi
   tự động (Notifier ghi nhận), không có bản ghi chờ duyệt.
3. **Quét 1 mã bất thường, confidence thấp:** `POST /scan` → tạo bản ghi chờ
   duyệt; gọi `POST /approvals/{id}/approve` → alert được gửi; ngược lại
   `reject` → không gửi, lý do được lưu.
4. **Đề xuất đổi ngưỡng:** EvalAgent output có config proposal → luôn tạo
   bản ghi chờ duyệt Gate 2 dù confidence cao thế nào.
5. **Hỏi-đáp đơn giản:** `POST /chat` hỏi giá 1 mã trong watchlist → trả lời
   đúng, không có bản ghi chờ duyệt nào được tạo.
6. **Hỏi-đáp cần giải thích:** `POST /chat` hỏi "tại sao mã X giảm" → trả
   lời có nhắc tới tin tức/lý do cụ thể (không phải câu trả lời chung chung).
7. **Cron trigger giả lập:** gọi thủ công job định kỳ cho watchlist nhiều mã
   → mỗi mã chạy luồng giám sát độc lập, một mã lỗi không chặn các mã khác.

## Ngoài phạm vi test MVP

- Load test / concurrency thật (nhiều user cùng lúc).
- Test độ chính xác tuyệt đối của LLM (dùng LLM-as-judge nếu cần, không bắt
  buộc cho MVP — xem `agent_eval.py` cũ như tài liệu tham khảo khi cần).
- Test tích hợp với nguồn dữ liệu giá/tin thật trong CI (dùng fake/mock, chỉ
  test thật thủ công khi cần xác nhận nguồn dữ liệu hoạt động).
