# Product Spec — Portfolio Watch (Quality Loop + Split Deploy)

## App goal

Xây dựng bản Portfolio Watch dễ demo và đáng tin: người dùng theo dõi vài mã
cổ phiếu VN, nhận cảnh báo bất thường (có duyệt khi cần), và hỏi–đáp dựa trên
giá/tin thật — trong khi hệ thống **trả lời đúng theo bộ câu hỏi mẫu**, **tách
UI / API / AI**, **hiện từng bước agent trên giao diện**, và **trace được trên
Langfuse**.

Nền tảng: MVP multi-agent đã có. Vòng này không viết lại từ đầu; tập trung
siết chất lượng và tách triển khai.

## Target users

| Vai trò | Nhu cầu |
|---|---|
| Người dùng demo | Xem watchlist, chat, thấy bước agent, duyệt cảnh báo |
| Người phát triển / coding agent | Chạy eval từng case golden, sửa multi-agent đến khi pass |

Không có đăng nhập / nhiều tenant ở vòng này.

## Core user flow

### 1) Chat (người dùng)

1. Mở Frontend → gửi câu hỏi về mã đang theo dõi.
2. Frontend gọi Backend; Backend gọi AI (không gọi AI từ trình duyệt).
3. UI hiện lần lượt các bước (ví dụ: chuẩn hoá câu hỏi → chọn agent → lấy
   giá/tin → soạn trả lời → kiểm tra an toàn).
4. Hiện câu trả lời cuối. Nếu Langfuse bật → có 1 trace cho lần hỏi đó.

### 2) Giám sát & duyệt (người dùng)

1. Thêm mã vào watchlist / đặt ngưỡng.
2. Quét một mã (hoặc để cron) → AI phân loại bình thường / bất thường.
3. Cảnh báo tự gửi hoặc chờ duyệt → người dùng approve / reject trên UI
   (qua Backend).

### 3) Siết chất lượng (developer)

1. Chọn **một** case trong golden dataset.
2. Chạy eval (rule + judge + đánh giá kết quả / đường đi agent).
3. Fail → sửa multi-agent hoặc prompt (không “nới” điểm để qua) → ghi task
   còn thiếu nếu cần năng lực mới → chạy lại **đúng case đó**.
4. Pass → sang case tiếp; mục tiêu: **pass hết** case (nhóm chèn chỉ dẫn giả
   phải pass 100%).

## Features in scope

- Giữ đủ luồng sản phẩm MVP: watchlist, quét/cảnh báo, HITL duyệt, chat.
- Golden dataset (~30 case) + eval từng case; thêm chấm **kết quả cuối** và
  **đường đi multi-agent** (ý tưởng từ `llm-engineer-demo`).
- Cải thiện multi-agent / prompt khi case fail; cập nhật backlog task thiếu.
- Tách 3 phần deploy độc lập:
  - **Frontend** — UI (chat + timeline bước + watchlist + duyệt).
  - **Backend** — API sản phẩm, proxy tới AI, stream/hiện bước; không chứa
    logic agent nặng.
  - **AI service** — multi-agent (tái dùng code hiện có), API nội bộ.
- UI hiện danh sách bước đang/đã chạy khi chat (scan nếu làm được cùng
  pattern).
- Langfuse: 1 request → 1 trace cha + span theo bước; tắt monitoring vẫn
  chat bình thường.
- Cấu hình URL/CORS bằng biến môi trường.

## Features out of scope

- Auth / multi-tenant thật.
- Email hoặc push cảnh báo thật.
- Fine-tune model, RAG tài liệu dài, đổi hàng loạt nguồn giá/tin.
- CI bắt buộc chạy full golden trên mọi PR.
- UI polish / design system lớn.
- Viết lại toàn bộ MVP từ đầu.
- Graph editor phức tạp cho agent (chỉ cần timeline bước đơn giản).

## Acceptance criteria

1. Eval trên golden: báo cáo pass/fail từng case; **toàn bộ case pass** theo
   scorer đã chốt trong test-plan (rule + judge + đánh giá kết quả cuối).
2. Nhóm case injection / chèn chỉ dẫn giả: **pass 100%**.
3. Mọi case từng fail đã xử lý: có ghi chú nguyên nhân + thay đổi; task mới
   (nếu có) nằm trong implementation-plan.
4. Frontend, Backend, AI chạy **3 process / 3 URL** độc lập.
5. Chat trên UI: thấy timeline bước và câu trả lời cuối.
6. Chat thành công với monitoring bật → thấy đúng 1 trace trên Langfuse.
7. Backend chỉ gọi AI qua HTTP — không import graph/agent domain.
8. Người dùng vẫn làm được: thêm watchlist, quét mã, duyệt cảnh báo, hỏi chat
   (qua kiến trúc tách lớp).
