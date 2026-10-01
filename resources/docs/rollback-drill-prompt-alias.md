# Rollback Drill (Prompt Alias)

Tài liệu mô phỏng tình huống sự cố khi sử dụng sai phiên bản prompt trong môi trường production và cách phục hồi nhanh chóng.

## Kịch Bản Sự Cố (Scenario)
- **Sự cố**: Phiên bản prompt mới được gắn nhãn alias `production` tại `resources/prompts/` hoặc registry bị lỗi, gây ra tỷ lệ trả lời sai cao hoặc vi phạm định dạng.
- **Phát hiện**: Cảnh báo từ công cụ Monitor (Langfuse) cho thấy tỷ lệ đánh giá thumbs-down tăng cao trong vòng 10 phút qua (Dữ liệu từ `hitl_feedback.json`).
- **Phạm vi ảnh hưởng**: Khách hàng đang nhận câu trả lời thiếu thông tin hoặc sai lệch từ `composer_node`.

## Hành Động Khắc Phục (Action)
1. Xác định phiên bản prompt ổn định trước đó (ví dụ: `v1.2`).
2. Mở file cấu hình alias hoặc trực tiếp trên hệ thống registry, trỏ alias `production` về lại `v1.2`.
   - Nếu quản lý qua file, sửa đổi trong file JSON/YAML tương ứng ở `resources/prompts/` và commit nhanh hoặc thay đổi thông qua biến môi trường.
3. Khởi động lại service hoặc xóa cache semantic/exact để cache ghi nhận `prompt_version` mới (thực tế chỉ cần key `prompt_version` thay đổi thì cache tự động làm mới do cache đã hỗ trợ lưu key kèm version).

## Xác Minh & Nghiệm Thu (Verify)
- Chạy lại bài kiểm tra cú pháp và chất lượng `prompt_lint` để chắc chắn file prompt không bị lỗi định dạng.
- Chạy lệnh eval-gate nội bộ với subset 20 câu (`python -m backend.eval.run --subset`) để chắc chắn mô hình đang trả lời đúng định dạng và điểm rule pass rate > baseline.
- Xác nhận các request gọi về đúng phiên bản prompt ổn định.
