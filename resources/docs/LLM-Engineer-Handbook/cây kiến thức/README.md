# Cây Kiến Thức LLM Engineer Handbook

Dự án trực quan hóa toàn bộ nội dung của **LLM Engineer Handbook** thành một **Cây kiến thức tương tác (Interactive Knowledge Tree)** bằng HTML5, CSS3 và Vanilla JavaScript.

Dự án được xây dựng theo phương pháp **Spec-Driven Development (SDD)**, tuân thủ nguyên tắc triển khai từng bước, tập trung vào MVP và có kiểm soát chất lượng qua từng phase.

---

## 1. Giới thiệu dự án

Khóa học **LLM Engineer Handbook** bao gồm 3 Module lớn với 25 bài học thực chiến chuyên sâu và 167 chủ đề kiến thức:
- **Module Giới thiệu**: Cấu trúc tổng thể và phương pháp học.
- **Module I: LLM, Prompt, RAG & Vector DB** (9 bài học).
- **Module II: AI Agent** (8 bài học).
- **Module III: Production LLMOps** (8 bài học).

**Mục tiêu ứng dụng:**
Cung cấp giao diện trực quan dạng cây phân cấp (Tree View):
- Nhánh cấp 1: Module.
- Nhánh cấp 2: Bài học.
- Nhánh cấp 3: Thư mục nhỏ / Chủ đề thành phần của từng bài.
- Khi người dùng nhấp vào từng nhánh hoặc thư mục con, khối nội dung tương ứng sẽ được mở rộng (expand/collapse) và hiển thị chi tiết kiến thức, mã nguồn mẫu, bảng so sánh và mẹo thực chiến trích xuất trực tiếp từ tài liệu gốc.

---

## 2. Cấu trúc thư mục dự án

Toàn bộ mã nguồn và đặc tả kỹ thuật được quản lý độc lập bên trong thư mục này:

```txt
cây kiến thức/
├── bando-tuduy-llm-engineer.html   # Bản đồ tư duy SVG tương tác toàn diện (Nền sáng, mở sẵn tầng 4)
├── bando-tuduy-llm-engineer.md     # Bản đồ tư duy toàn văn dạng Markdown (7.009 dòng cho XMind/Obsidian)
├── README.md                       # Hướng dẫn tổng quan và tra cứu
├── AGENTS.md                       # Quy tắc và hướng dẫn hành vi cho AI coding agent
├── index.html                      # Giao diện ứng dụng web cây kiến thức
├── styles.css                      # Bảng màu, layout và responsive styles
├── app.js                          # Logic điều khiển cây và tìm kiếm
├── knowledge-data.js               # Cơ sở dữ liệu tri thức 25 bài học & 167 chủ đề
└── specs/
    ├── product-spec.md             # Đặc tả sản phẩm
    ├── implementation-plan.md      # Kế hoạch triển khai
    ├── test-plan.md                # Kế hoạch kiểm thử
    └── change-log.md               # Lịch sử thay đổi
```

---

## 3. Yêu cầu môi trường (Prerequisites)

Ứng dụng được thiết kế siêu nhẹ, thuần Client-side (Vanilla JS), do đó:
- **Tối thiểu:** Bất kỳ trình duyệt web hiện đại nào (Google Chrome, Microsoft Edge, Mozilla Firefox, Brave, Safari).
- **Tùy chọn (để chạy local server):**
  - Python 3.8+ (khuyên dùng, thường có sẵn trên Windows/Mac/Linux)
  - Hoặc Node.js 16+ (nếu thích dùng `npx`)

---

## 4. Hướng dẫn chạy ứng dụng ở Local

### Cách 1: Mở trực tiếp bằng trình duyệt (Không cần cài đặt gì thêm)
1. Mở File Explorer trên máy tính.
2. Tìm đến thư mục:
   `d:\Hoc_Tap\YOURClass\LLM-Engineer-Handbook\cây kiến thức\`
3. Nhấp đúp chuột vào file **`index.html`** để mở trực tiếp trên trình duyệt mặc định.

---

### Cách 2: Chạy qua Python HTTP Server (Khuyên dùng)
Chạy qua local server giúp đảm bảo hiệu năng tải trang và tương thích tốt nhất:

1. Mở PowerShell hoặc Command Prompt tại thư mục dự án:
   ```powershell
   cd "d:\Hoc_Tap\YOURClass\LLM-Engineer-Handbook\cây kiến thức"
   ```
2. Khởi chạy server trên cổng `3000`:
   ```powershell
   python -m http.server 3000
   ```
   *(Nếu cổng 3000 đang được dùng bởi app khác, bạn có thể đổi thành `python -m http.server 8080`)*
3. Mở trình duyệt và truy cập:
   ```text
   http://localhost:3000
   ```

---

### Cách 3: Chạy qua Node.js (npx serve)
Nếu bạn có sẵn môi trường Node.js:
```powershell
cd "d:\Hoc_Tap\YOURClass\LLM-Engineer-Handbook\cây kiến thức"
npx serve . -l 3000
```
Truy cập: `http://localhost:3000`

---

## 5. Kiểm tra ứng dụng hoạt động chính xác

Sau khi mở ứng dụng:
1. **Kiểm tra giao diện:**
   - Cột bên trái hiển thị Cây kiến thức với 4 Modules và thanh công cụ tìm kiếm.
   - Cột bên phải hiển thị Màn hình chào mừng với 3 thẻ số liệu thống kê: **3 Modules, 25 Bài học, 167 Chủ đề**.
2. **Kiểm tra Developer Tools (F12):**
   - Nhấn phím `F12` (hoặc `Ctrl + Shift + I`), chọn tab **Console**.
   - Bạn sẽ thấy dòng log xác nhận nạp dữ liệu thành công:
     ```text
     🌳 [Knowledge Tree] Initializing application...
     📚 [Knowledge Base] Loaded 3 Modules, 25 Lessons, 167 Topics.
     ✅ [Knowledge Tree] Phase 5: Fully Initialized & Verified.
     ```
   - Không xuất hiện bất kỳ thông báo lỗi đỏ (`Uncaught Error`) nào.

---

## 6. Xử lý sự cố thường gặp (Troubleshooting)

| Vấn đề | Nguyên nhân khả dĩ | Giải pháp khắc phục |
|---|---|---|
| **Cổng 3000 bị báo lỗi `Address already in use`** | Đang có một tiến trình khác (React, Next.js, Docker, v.v.) chiếm port 3000 | Đổi sang port khác: `python -m http.server 3001` hoặc `8080` |
| **Trang hiển thị trống hoặc không có cây** | Trình tự tải file script bị sai hoặc file `knowledge-data.js` bị thiếu | Mở file `index.html`, đảm bảo thẻ `<script src="knowledge-data.js"></script>` luôn nằm trước `<script src="app.js"></script>` |
| **Giao diện không cập nhật sau khi sửa code** | Trình duyệt đang lưu bộ nhớ đệm (Browser Cache) | Nhấn tổ hợp phím `Ctrl + F5` (hoặc `Ctrl + Shift + R`) để tải lại toàn bộ tài nguyên mới |
| **Không hiển thị font chữ Google Fonts** | Máy tính đang ở chế độ offline không có mạng | Ứng dụng đã cấu hình font fallback hệ thống (`-apple-system, BlinkMacSystemFont, Segoe UI, Roboto`), giao diện vẫn hiển thị đẹp và đầy đủ |

---

## 7. Demo từ xa bằng ngrok (Demo with ngrok)

ngrok cho phép tạo một đường hầm an toàn (secure HTTPS tunnel) từ máy local của bạn ra internet để gửi demo cho người khác xem trực tiếp trên điện thoại hoặc máy tính từ xa.

### 7.1. Cài đặt ngrok
Chọn một trong các cách sau:
- **Cách 1 (Khuyên dùng trên Windows):** Cài qua winget trong PowerShell:
  ```powershell
  winget install ngrok
  ```
- **Cách 2:** Tải trực tiếp file `.zip` tại [ngrok.com/download](https://ngrok.com/download), giải nén và đưa vào thư mục PATH.
- **Cách 3 (Dành cho người có Node.js):** Chạy trực tiếp qua npx không cần cài:
  ```powershell
  npx @ngrok/ngrok http 3000
  ```

---

### 7.2. Lấy Auth Token và cấu hình (Chỉ cần làm lần đầu)
1. Đăng ký tài khoản miễn phí tại: [dashboard.ngrok.com/signup](https://dashboard.ngrok.com/signup).
2. Lấy Authtoken cá nhân tại: [dashboard.ngrok.com/get-started/your-authtoken](https://dashboard.ngrok.com/get-started/your-authtoken).
3. Thêm token vào ngrok bằng lệnh:
   ```powershell
   ngrok config add-authtoken <YOUR_AUTHTOKEN_HERE>
   ```

---

### 7.3. Khởi chạy Demo qua ngrok

Mở 2 cửa sổ Terminal (PowerShell):

- **Terminal 1: Khởi động local server**
  ```powershell
  cd "d:\Hoc_Tap\YOURClass\LLM-Engineer-Handbook\cây kiến thức"
  python -m http.server 3000
  ```

- **Terminal 2: Mở tunnel ra internet**
  ```powershell
  ngrok http 3000
  ```

Sau khi chạy lệnh, ngrok sẽ hiển thị thông tin phiên kết nối dạng:
```text
Session Status                online
Account                       Your Name (Plan: Free)
Forwarding                    https://xxxx-xxxx-xxxx.ngrok-free.app -> http://localhost:3000
```
Sao chép đường link **`https://xxxx-xxxx-xxxx.ngrok-free.app`** và gửi cho đồng nghiệp, học viên hoặc mentor để cùng trải nghiệm.

---

### 7.4. Kịch bản trình diễn Demo mẫu (Demo Script Checklist)

Khi trình bày sản phẩm cho người khác, bạn có thể thực hiện theo quy trình 6 bước chuẩn mực sau:

- [ ] **Bước 1 — Mở trên thiết bị di động:** Gửi link ngrok sang điện thoại cá nhân và mở trên trình duyệt mobile để minh họa ứng dụng có độ tương thích cao (Responsive Design).
- [ ] **Bước 2 — Giới thiệu tổng quan:** Tại màn hình chào mừng (Welcome View), giới thiệu quy mô tri thức của khóa học: **3 Modules chuyên sâu, 25 Bài học thực chiến, 167 Chủ đề kiến thức**.
- [ ] **Bước 3 — Trải nghiệm Cây phân cấp:** Nhấp chuột vào `Module II: AI Agent` -> nhấp tiếp vào `Bài 2: Building Agents với LangGraph` -> giải thích cấu trúc phân tầng trực quan của cây tri thức.
- [ ] **Bước 4 — Xem chi tiết bài đọc & Code:** Chọn một mục con (ví dụ: *LangGraph Core Concepts* hoặc *Chat Completions*), chỉ rõ thanh Breadcrumbs, lý thuyết cốt lõi, bảng so sánh và nhấn nút **Copy** mã nguồn để minh họa trải nghiệm người dùng mượt mà.
- [ ] **Bước 5 — Tìm kiếm thông minh Realtime:** Gõ từ khóa `RAG` hoặc `LangGraph` vào ô tìm kiếm -> chỉ rõ tính năng tự động mở rộng nhánh cha, bôi màu vàng nổi bật từ khóa và badge đếm số lượng kết quả trùng khớp. Sau đó bấm `Escape` hoặc nút `&times;` để đưa cây về nguyên trạng.
- [ ] **Bước 6 — Điều khiển cây quy mô lớn:** Sử dụng nút **"Mở tất cả"** (Expand All) để hiển thị toàn bộ 167 chủ đề cùng lúc, và nút **"Thu gọn"** (Collapse All) để đóng gọn gàng về các Module lớn.
