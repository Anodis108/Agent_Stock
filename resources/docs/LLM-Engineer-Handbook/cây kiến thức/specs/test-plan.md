# Test Plan: Cây Kiến Thức LLM Engineer Handbook

Kế hoạch kiểm thử chất lượng cho ứng dụng Cây Kiến Thức LLM Engineer Handbook theo phương pháp Spec-Driven Development.

---

## 1. Mục tiêu kiểm thử
- Đảm bảo cấu trúc cây hiển thị chính xác, đầy đủ toàn bộ nội dung của khóa học LLM Engineer Handbook.
- Đảm bảo các tương tác đóng/mở (expand/collapse) mượt mà, trực quan, không phát sinh lỗi giao diện.
- Đảm bảo việc hiển thị kiến thức chi tiết của từng nhánh mục con chính xác, dễ đọc và đầy đủ code mẫu.
- Đảm bảo tính năng tìm kiếm và các công cụ điều khiển cây hoạt động nhanh, chính xác.

---

## 2. Phạm vi kiểm thử (Scope)

### Trong phạm vi (In-Scope)
- Kiểm thử cấu trúc dữ liệu cây (Đầy đủ 3 Module, 25 bài học và các mục con).
- Kiểm thử giao diện và tương tác (Tree View, Content Panel, Breadcrumbs, Expand/Collapse).
- Kiểm thử thanh công cụ tiện ích (Tìm kiếm từ khóa, Expand All, Collapse All).
- Kiểm thử khả năng hiển thị đa màn hình (Responsive Design).
- Kiểm thử hoạt động offline/local trên các trình duyệt phổ biến.

### Ngoài phạm vi (Out-of-Scope)
- Tải trọng server (ứng dụng chạy hoàn toàn tĩnh ở client).
- Kiểm thử xác thực hay bảo mật đăng nhập (MVP không có authentication).

---

## 3. Danh sách Test Cases chi tiết

### TC-01: Khởi động và hiển thị ban đầu
- **Mục tiêu:** Kiểm tra ứng dụng tải trang thành công mà không có lỗi.
- **Các bước thực hiện:**
  1. Mở file `index.html` trên trình duyệt Chrome/Edge/Firefox.
  2. Mở Developer Tools (F12) kiểm tra tab Console.
- **Kết quả kỳ vọng:**
  - Trang web tải nhanh, hiển thị tiêu đề "Cây Kiến Thức LLM Engineer Handbook".
  - Hiển thị root node và 3 Module lớn.
  - Không có bất kỳ thông báo lỗi đỏ (Error) nào trong Console.
- **Trạng thái:** [ĐẠT - PASSED]

---

### TC-02: Kiểm tra dữ liệu bao quát đầy đủ
- **Mục tiêu:** Đảm bảo toàn bộ 25 bài học của 3 Module đều có mặt trên cây.
- **Các bước thực hiện:**
  1. Mở nhánh Module I -> đếm số bài học (kỳ vọng 9 bài).
  2. Mở nhánh Module II -> đếm số bài học (kỳ vọng 8 bài).
  3. Mở nhánh Module III -> đếm số bài học (kỳ vọng 8 bài).
  4. Mở nhánh Giới thiệu tổng quan.
- **Kết quả kỳ vọng:**
  - Đầy đủ 25 bài học theo đúng thứ tự nội dung trong tài liệu gốc.
  - Mỗi bài học đều có các nhánh con tương ứng với các phần lý thuyết/thực hành chính.
- **Trạng thái:** [ĐẠT - PASSED] (3 Modules, 25 bài học, 167 chủ đề)

---

### TC-03: Tương tác Đóng / Mở (Expand / Collapse)
- **Mục tiêu:** Kiểm tra hoạt động mở/đóng từng cấp của cây.
- **Các bước thực hiện:**
  1. Click vào icon hoặc tên của Module I.
  2. Click tiếp vào "Bài 1: LLM APIs Hands-on".
  3. Click lại vào "Bài 1: LLM APIs Hands-on".
- **Kết quả kỳ vọng:**
  - Lần click 1: Danh sách bài học của Module I mở ra mượt mà, icon chuyển trạng thái mở.
  - Lần click 2: Các mục con của Bài 1 xổ ra.
  - Lần click 3: Các mục con của Bài 1 thu gọn lại, các bài khác không bị ảnh hưởng.
- **Trạng thái:** [ĐẠT - PASSED]

---

### TC-04: Hiển thị chi tiết kiến thức khi nhấp chọn nhánh
- **Mục tiêu:** Kiểm tra việc xem nội dung chi tiết của một mục nhỏ.
- **Các bước thực hiện:**
  1. Mở Module I > Bài 1 > Click vào mục con "1. Chat Completions".
  2. Quan sát khung hiển thị bên phải (hoặc bên dưới).
- **Kết quả kỳ vọng:**
  - Nhánh con được đánh dấu trạng thái "Active" (đổi màu nổi bật).
  - Khung chi tiết hiển thị breadcrumbs: `Module I > Bài 1 > 1. Chat Completions`.
  - Hiển thị đầy đủ phần lý thuyết cốt lõi, bảng cấu trúc message, và khối code mẫu Python.
- **Trạng thái:** [ĐẠT - PASSED]

---

### TC-05: Tìm kiếm và lọc theo từ khóa
- **Mục tiêu:** Kiểm tra chức năng lọc nhánh kiến thức theo từ khóa.
- **Các bước thực hiện:**
  1. Nhập từ khóa `LangGraph` vào ô tìm kiếm.
  2. Quan sát cây kiến thức.
  3. Xóa từ khóa trong ô tìm kiếm.
- **Kết quả kỳ vọng:**
  - Cây tự động mở các nhánh liên quan đến `LangGraph` (Module II, Bài 2).
  - Làm nổi bật từ khóa trùng khớp.
  - Khi xóa ô tìm kiếm, cây khôi phục về trạng thái bình thường.
- **Trạng thái:** [ĐẠT - PASSED]

---

### TC-06: Thao tác Expand All và Collapse All
- **Mục tiêu:** Kiểm tra các nút điều khiển cây trên thanh công cụ.
- **Các bước thực hiện:**
  1. Nhấn nút "Mở tất cả" (Expand All).
  2. Nhấn nút "Thu gọn tất cả" (Collapse All).
- **Kết quả kỳ vọng:**
  - Nhấn "Mở tất cả": Toàn bộ các nhánh của tất cả các Module và bài học đều đồng loạt mở ra.
  - Nhấn "Thu gọn tất cả": Cây thu gọn về trạng thái các Module ban đầu.
- **Trạng thái:** [ĐẠT - PASSED]

---

### TC-07: Hiển thị trên thiết bị di động / màn hình hẹp
- **Mục tiêu:** Kiểm tra tính thân thiện responsive.
- **Các bước thực hiện:**
  1. Thu nhỏ kích thước cửa sổ trình duyệt xuống 400px (Mobile view).
  2. Kiểm tra thanh cuộn, kích thước font chữ, và việc chuyển đổi giữa danh sách cây và khung xem chi tiết.
- **Kết quả kỳ vọng:**
  - Giao diện tự động co dãn hợp lý, không bị vỡ layout hoặc tràn màn hình ngang.
  - Người dùng có thể dễ dàng chạm mở cây và đọc chi tiết kiến thức.
- **Trạng thái:** [ĐẠT - PASSED]
