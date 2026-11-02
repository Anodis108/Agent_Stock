# Product Spec: Cây Kiến Thức LLM Engineer Handbook

## 1. App Name
**Cây Kiến Thức LLM Engineer Handbook (Interactive Knowledge Tree)**

---

## 2. Goal
- Chuyển đổi toàn bộ nội dung từ tài liệu [LLM-Engineer-Handbook](file:///d:/Hoc_Tap/YOURClass/LLM-Engineer-Handbook) (gồm phần Giới thiệu và 3 Module chuyên sâu với 25 bài học thực chiến) thành một trang web đơn giản, trực quan dưới dạng **cây kiến thức tương tác (Interactive Collapsible Tree)**.
- Giúp người học và kỹ sư AI dễ dàng nắm bắt bức tranh toàn cảnh, tra cứu nhanh kiến thức theo từng tầng phân cấp (Module -> Bài học -> Thư mục con/Chủ đề -> Nội dung chi tiết), có thể đóng/mở linh hoạt và xem code mẫu minh họa mà không phải lướt qua hàng chục nghìn dòng tài liệu dài.

---

## 3. Target Users
- **Học viên khóa học LLM Engineer:** Cần sơ đồ hệ thống hóa bài học, theo dõi mạch kiến thức và tra cứu nhanh khi làm bài tập hoặc thực hành dự án.
- **Kỹ sư AI / Lập trình viên:** Cần một cuốn cẩm nang tra cứu nhanh (cheat sheet) về API, LangGraph, RAG pipeline, fine-tuning và tối ưu hóa hệ thống LLM khi làm việc thực tế.
- **Người tự học:** Cần một lộ trình trực quan, rõ ràng để định hướng việc học từ nền tảng đến production.

---

## 4. Core User Flow
1. **Khởi chạy ứng dụng:** Người dùng mở file `index.html` trong trình duyệt web (hoặc qua local server).
2. **Quan sát tổng quan:** Màn hình chia bố cục trực quan:
   - Cột bên trái: Cây thư mục kiến thức (Tree View).
   - Cột bên phải: Khung hiển thị chi tiết nội dung (Content View).
3. **Duyệt cây phân cấp:**
   - Cây hiển thị mặc định ở cấp Module (`Giới thiệu`, `Module I`, `Module II`, `Module III`).
   - Người dùng click vào tên hoặc icon của Module để mở ra danh sách bài học (Bài 1, Bài 2, ...).
   - Click tiếp vào một bài học để xổ ra các thư mục con / chủ đề kiến thức cụ thể (ví dụ: `Chat Completions`, `Parameters`, `Streaming`, `Rate Limits`).
4. **Xem chi tiết kiến thức:**
   - Khi click vào bất kỳ mục con nào ở cấp cuối cùng, khung bên phải sẽ lập tức hiển thị nội dung chi tiết: tóm tắt lý thuyết, bảng dữ liệu, và khối code ví dụ có định dạng rõ ràng.
   - Nhánh đang được chọn sẽ hiển thị trạng thái nổi bật (Active State) kèm thanh Breadcrumb chỉ rõ vị trí (`Module > Bài học > Chủ đề`).
5. **Tra cứu & Điều khiển tiện ích:**
   - Người dùng có thể gõ từ khóa vào ô tìm kiếm để lọc ngay các nhánh liên quan.
   - Nhấn nút "Mở tất cả" (Expand All) hoặc "Thu gọn tất cả" (Collapse All) để tùy chỉnh chế độ xem cây.

---

## 5. Features In Scope (MVP)

1. **Cây kiến thức phân tầng tương tác (Collapsible Tree View):**
   - Phân cấp 4 tầng: Gốc (Handbook) -> Module (3 module + giới thiệu) -> Bài học (25 bài) -> Đề mục nhỏ/Chủ đề.
   - Hỗ trợ đóng/mở (expand/collapse) mượt mà cho từng nhánh.
   - Icon trực quan phân biệt Module, Bài học và Chủ đề con.

2. **Khung hiển thị chi tiết kiến thức (Content View Panel):**
   - Hiển thị đầy đủ kiến thức của mục con được chọn: lý thuyết, bảng đối chiếu, code mẫu.
   - Khối code có syntax highlighting dễ đọc.
   - Thanh Breadcrumb hiển thị đường dẫn định vị mục hiện tại.
   - Màn hình chào mặc định (Welcome State) khi chưa chọn mục nào.

3. **Dữ liệu kiến thức bao quát đầy đủ:**
   - Tích hợp 100% nội dung cốt lõi từ 25 bài học của 3 Module trong handbook:
     - *Module I: LLM, Prompt, RAG & Vector DB* (9 bài).
     - *Module II: AI Agent* (8 bài).
     - *Module III: Production LLMOps* (8 bài).
     - *Phần Giới thiệu & Lộ trình*.

4. **Thanh công cụ điều khiển cây (Toolbar):**
   - Ô tìm kiếm lọc realtime theo tên bài học/chủ đề.
   - Nút "Mở tất cả" (Expand All).
   - Nút "Thu gọn tất cả" (Collapse All).

5. **Kiến trúc tĩnh, siêu nhẹ (Client-side Only):**
   - Chạy trực tiếp bằng HTML5, Modern CSS và Vanilla JavaScript.
   - Không phụ thuộc backend, không cần database, nạp tức thì.

---

## 6. Features Out of Scope (Không thuộc MVP)
- Hệ thống tài khoản, đăng nhập, phân quyền người dùng.
- Tính năng chỉnh sửa hoặc ghi chú thêm trực tiếp trên giao diện web.
- Đánh dấu tiến độ học tập (checkbox "Đã học", progress bar LMS).
- Hệ thống câu hỏi trắc nghiệm hoặc bài tập tương tác (Quiz).
- Đồng bộ đám mây realtime.
- Xuất dữ liệu ra file PDF hoặc sơ đồ mindmap ảnh.

---

## 7. Acceptance Criteria
- [ ] Ứng dụng chạy mượt mà trên các trình duyệt phổ biến (Chrome, Edge, Firefox, Safari) chỉ bằng cách mở file `index.html` hoặc chạy local HTTP server, không có lỗi console.
- [ ] Cây kiến thức bao quát đầy đủ cả 3 Module và toàn bộ 25 bài học của handbook.
- [ ] Thao tác nhấp chuột vào từng nhánh cây phản hồi ngay lập tức, đóng/mở các nhánh con mượt mà, đúng trạng thái icon.
- [ ] Nhấp vào mục con ở tầng cuối cùng sẽ hiển thị đúng và đủ nội dung chi tiết (lý thuyết, bảng dữ liệu, code ví dụ) sang khung bên phải.
- [ ] Ô tìm kiếm lọc chính xác các bài học/mục con có chứa từ khóa được nhập và tự động mở nhánh tương ứng.
- [ ] Nút "Mở tất cả" mở bung toàn bộ các nhánh; nút "Thu gọn tất cả" đóng cây lại về trạng thái ban đầu.
- [ ] Giao diện hiện đại, sạch đẹp, font chữ dễ nhìn, bố cục 2 cột cân đối và hỗ trợ cuộn độc lập cho từng cột.
