# Product Spec — Portfolio Watch & Chat Agent

## Mục tiêu sản phẩm (App Goal)

Xây dựng một hệ thống multi-agent **tự động giám sát danh mục cổ phiếu Việt
Nam** — phát hiện biến động giá/tin bất thường, đánh giá mức độ nghiêm
trọng, soạn cảnh báo và gửi đi (có kiểm soát qua HITL khi cần) — đồng thời
cho phép người dùng **hỏi-đáp tự do** về các mã họ theo dõi, trả lời dựa
trên dữ liệu giá/tin thật.

Vấn đề cần giải: nhà đầu tư cá nhân theo dõi vài mã cổ phiếu, nhưng không có
thời gian tự kiểm tra giá + tin tức mỗi ngày để nhận ra biến động bất thường
sớm. Khi hỏi "mã X dạo này sao rồi", họ cũng muốn câu trả lời có ngữ cảnh
(giá, tin liên quan) chứ không phải tự tra cứu nhiều nguồn.

## Đối tượng dùng (Target Users)

Một người dùng demo (không cần multi-tenant thật, không cần đăng ký/đăng
nhập phức tạp ở MVP) — có 1 watchlist gồm vài mã cổ phiếu.

## Luồng chính (Core User Flow)

**Luồng 1 — Giám sát chủ động (hệ thống tự chạy, người dùng không cần hỏi):**

1. Cron định kỳ (hoặc nút "Quét ngay" để demo 1 mã cụ thể) → hệ thống đọc
   watchlist, lấy giá mới nhất + tin liên quan cho từng mã.
2. Hệ thống phân loại: bình thường → dừng, chỉ ghi log. Bất thường → đánh
   giá mức độ nghiêm trọng (kèm bằng chứng).
3. Hệ thống soạn nội dung cảnh báo, kiểm tra guardrail (không lời khuyên
   mua/bán chắc chắn, khớp bằng chứng thật).
4. Nếu độ tin cậy cao và khớp ngưỡng người dùng đã đặt → gửi cảnh báo ngay.
   Nếu không → chờ người dùng duyệt (HITL) trước khi gửi.
5. Nếu hệ thống đề xuất đổi ngưỡng cảnh báo/thêm mã liên quan → luôn chờ
   người dùng duyệt riêng, không tự động áp dụng.

**Luồng 2 — Hỏi-đáp theo yêu cầu (người dùng chủ động hỏi):**

1. Người dùng gửi câu hỏi tự do (vd: "mã X dạo này sao rồi", "tại sao giá Y
   giảm") qua Chat API.
2. Hệ thống chuẩn hoá câu hỏi (dùng lịch sử hội thoại nếu cần), xác định câu
   hỏi cần agent nào (chỉ tra cứu giá/tin, hay cần giải thích/so sánh).
3. Hệ thống gọi đúng agent cần thiết, tổng hợp kết quả, soạn câu trả lời dựa
   trên dữ liệu thật, qua guardrail.
4. Trả lời ngay cho người dùng — không qua bước duyệt nào, vì đây chỉ là
   cung cấp thông tin, không có tác dụng phụ ra bên ngoài.

Chi tiết từng agent tham gia 2 luồng trên: xem [specs/agents.md](agents.md).

## Tính năng trong phạm vi (In Scope)

- 3 lối vào: API "quét ngay" (chọn 1 mã, dùng để demo), Cron trigger định kỳ
  (giám sát tự động), Chat API (hỏi tự do).
- Luồng giám sát đầy đủ: PriceAgent + NewsAgent → Event Classifier →
  EvalAgent (khi bất thường) → SynthesisAgent → Guardrail → Confidence Gate
  → gửi tự động hoặc HITL Gate 1.
- Luồng hỏi-đáp đầy đủ: Rewrite → Supervisor routing → gọi lại
  PriceAgent/NewsAgent → (EvalAgent nếu cần giải thích/so sánh) →
  AnswerComposer → Guardrail → trả lời, lưu hội thoại vào Memory.
- HITL Gate 1 (duyệt gửi cảnh báo khi tin cậy thấp) và HITL Gate 2 (duyệt đổi
  watchlist/ngưỡng) — implement dưới dạng API chờ duyệt (poll hoặc endpoint
  approve/reject), không cần UI phức tạp.
- Watchlist Store, Price History DB, Memory Store — có thể dùng SQLite/file
  JSON cho MVP, miễn tách interface rõ ràng (đổi sang Postgres sau không khó).
- "Gửi cảnh báo" ở MVP: log ra console/lưu DB là đủ, KHÔNG bắt buộc tích hợp
  email/push thật (có thể để interface + fake implementation).
- Frontend: 1 trang đơn giản (chat box + xem watchlist + danh sách cảnh báo
  chờ duyệt), không cần polish UI.

## Tính năng ngoài phạm vi (Out of Scope — MVP)

- Multi-tenant/auth thật (nhiều user, đăng nhập).
- Gửi email/push thật (SMTP, FCM...).
- Tích hợp nguồn dữ liệu giá/tin thật đa dạng — 1 nguồn giá + 1 nguồn tin
  (cafef) là đủ, miễn interface cho phép thêm nguồn sau.
- Fine-tune model, RAG trên tài liệu dài hạn.
- Observability dashboard riêng — tái dùng tracing đã có ở llm-engineer-demo
  (LangFuse) nếu có sẵn key, không bắt buộc.

## Tiêu chí chấp nhận (Acceptance Criteria)

- Gọi API "quét ngay" cho 1 mã → thấy toàn bộ luồng chạy: giá, tin, phân
  loại sự kiện, (nếu bất thường) đánh giá + soạn cảnh báo + gate.
- Đặt watchlist có ngưỡng thấp → cảnh báo tự sinh ra khi giá biến động vượt
  ngưỡng, xuất hiện ở trạng thái "chờ duyệt" hoặc "đã gửi" tùy độ tin cậy.
- Approve/reject một cảnh báo chờ duyệt qua API → trạng thái cập nhật đúng,
  lý do reject được ghi lại.
- Đề xuất đổi ngưỡng từ EvalAgent → luôn nằm ở trạng thái chờ duyệt (Gate 2),
  không tự động áp dụng.
- Gửi câu hỏi tự do qua Chat API về 1 mã trong watchlist → nhận câu trả lời
  dựa trên dữ liệu giá/tin thật, không qua HITL.
- Guardrail chặn được câu trả lời/cảnh báo có lời khuyên mua/bán chắc chắn
  (test case cụ thể trong test-plan.md).
