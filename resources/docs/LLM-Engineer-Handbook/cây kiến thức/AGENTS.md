# AGENTS.md

Project này tuân theo phương pháp **Spec-Driven Development**.

Mọi AI coding agent khi làm việc trong project này phải tuân thủ các quy tắc sau:

---

## 1. Giới hạn phạm vi (Boundary)
- Toàn bộ thao tác (tạo file, sửa code, chạy lệnh) phải diễn ra **hoàn toàn bên trong thư mục `cây kiến thức/`**.
- Không chỉnh sửa, di chuyển hoặc xóa các tài liệu gốc ở thư mục cha (`00-gioi-thieu.md`, `module-*.md`, `llm-engineer-handbook-full.md`).

---

## 2. Nguyên tắc cốt lõi (Core Rules)
1. **Always read the specs before coding:** Luôn đọc kỹ các file trong `specs/` (`product-spec.md`, `implementation-plan.md`, `test-plan.md`) trước khi viết code.
2. **Implement only one phase or task at a time:** Chỉ triển khai duy nhất một task hoặc một phase tại một thời điểm. Không làm trước các phase tiếp theo.
3. **Keep the app simple:** Ưu tiên giải pháp đơn giản, rõ ràng, dễ bảo trì; không over-engineer.
4. **Do not add unnecessary libraries:** Tránh cài đặt thêm các thư viện phức tạp không cần thiết; ưu tiên Vanilla HTML/CSS/JS.
5. **Do not change architecture unless the spec is updated:** Giữ đúng cấu trúc đã định nghĩa trong `specs/product-spec.md`. Không tự ý thay đổi kiến trúc trừ khi spec được cập nhật trước.
6. **After each implementation, update specs/change-log.md:** Sau mỗi lần hoàn thành triển khai hoặc sửa lỗi, bắt buộc phải cập nhật nhật ký thay đổi.
7. **After each implementation, explain how to test the change:** Sau khi triển khai xong, phải giải thích rõ ràng các bước kiểm thử thủ công để người dùng kiểm chứng.

---

## 3. Workflow thực hiện cho mỗi task
Mỗi khi nhận yêu cầu triển khai:
1. Đọc lại `specs/product-spec.md` và `specs/implementation-plan.md`.
2. Xác định đúng một task hoặc phase chưa hoàn thành kế tiếp.
3. Trước khi viết code:
   - Tóm tắt việc sẽ làm.
   - Nêu rõ các file sẽ tạo hoặc chỉnh sửa.
   - Nêu cách sẽ kiểm tra kết quả.
4. Thực hiện code cho riêng task đó.
5. Đánh dấu hoàn thành `[x]` vào checklist trong `specs/implementation-plan.md`.
6. Cập nhật `specs/change-log.md`.
7. Cung cấp lệnh chạy và các bước kiểm thử chi tiết.
