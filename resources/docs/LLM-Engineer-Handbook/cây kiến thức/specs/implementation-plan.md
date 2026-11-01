# Implementation Plan: Cây Kiến Thức LLM Engineer Handbook

Kế hoạch triển khai dự án theo phương pháp Spec-Driven Development (SDD). Kế hoạch được chuẩn hóa thành 7 phase nhỏ với các checklist cụ thể. Mỗi lần triển khai chỉ tập trung vào một phase/task duy nhất.

---

## Phase 1: Project Setup
- [x] Khởi tạo các file khung sườn trong thư mục `cây kiến thức/`: `index.html`, `styles.css`, `app.js`
- [x] Thiết lập khung tài liệu HTML5 ngữ nghĩa, khai báo viewport, tiêu đề trang và nhúng các file CSS/JS
- [x] Xây dựng hệ thống biến CSS cơ bản trong `styles.css` (màu sắc chủ đạo, font chữ Google Fonts, biến khoảng cách, shadow)
- [x] Viết đoạn mã kiểm tra khởi tạo cơ bản trong `app.js` để xác nhận liên kết file hoạt động
- [x] Kiểm tra mở file `index.html` trên trình duyệt và xác nhận không có lỗi trong Console

---

## Phase 2: Core UI (Khung sườn Giao diện & Component Cây)
- [x] Xây dựng cấu trúc layout 2 cột: Sidebar bên trái (Cây thư mục) và Khu vực bên phải (Chi tiết nội dung)
- [x] Thiết lập CSS styling cho Sidebar cây thư mục (đường kẻ nhánh cây, khoảng thụt dòng phân cấp, hiệu ứng hover)
- [x] Thiết lập CSS styling cho icon các cấp (icon thư mục mở/đóng, icon tài liệu, icon code, badge đếm số lượng)
- [x] Thiết lập CSS styling cho Khung chi tiết bên phải (thanh Breadcrumbs, tiêu đề bài học, kiểu chữ nội dung, khối code mẫu)
- [x] Xây dựng trạng thái màn hình chờ mặc định (Welcome State) khi người dùng mới vào và chưa nhấp chọn nhánh nào
- [x] Thêm CSS responsive cơ bản để layout co dãn linh hoạt trên các kích thước màn hình

---

## Phase 3: Core Data Logic (Mô hình hóa & Trích xuất Dữ liệu Handbook)
- [x] Tạo file `knowledge-data.js` định nghĩa cấu trúc dữ liệu JSON chuẩn cho cây kiến thức
- [x] Trích xuất và cấu trúc hóa nội dung từ `00-gioi-thieu.md` (Tổng quan lộ trình)
- [x] Trích xuất và cấu trúc hóa nội dung từ `module-1-llm-prompt-rag-vectordb.md` (9 bài học: LLM APIs, Local LLMs, Fine-tuning, Vector DB, RAG, Agentic RAG, Evaluation, Production Optimization, Capstone)
- [x] Trích xuất và cấu trúc hóa nội dung từ `module-2-ai-agent.md` (8 bài học: What Is an Agent, LangGraph, Memory & Context, Tool Design, Agent Evaluation, Multi-Agent Systems, Capstone, Workshop)
- [x] Trích xuất và cấu trúc hóa nội dung từ `module-3-production-llmops.md` (8 bài học: Prompt Management, Evaluation Pipelines, Cost Optimization, Containerisation, Cloud Deployment, CI/CD, Observability, Capstone)
- [x] Xây dựng các hàm helper trong JS để truy vấn, duyệt và tìm kiếm node dữ liệu theo ID

---

## Phase 4: Connect UI to Data (Kết nối Cây dữ liệu & Tương tác)
- [x] Viết hàm render đệ quy duyệt đối tượng dữ liệu trong `knowledge-data.js` và tạo các phần tử DOM cây thư mục
- [x] Triển khai sự kiện click mở rộng/thu gọn (Expand/Collapse) trên từng nhánh Module và từng Bài học
- [x] Cập nhật hiệu ứng chuyển trạng thái icon (thư mục đóng -> thư mục mở, mũi tên xoay)
- [x] Triển khai sự kiện click chọn một mục con ở tầng cuối cùng để nạp nội dung chi tiết sang Khung bên phải
- [x] Cập nhật thanh Breadcrumb (`Module > Bài học > Chủ đề`) tương ứng với vị trí mục đang được chọn
- [x] Đánh dấu trạng thái nổi bật (Active State) cho nhánh đang được xem trên cây thư mục

---

## Phase 5: Validation, Error States & Utilities (Kiểm tra & Tiện ích)
- [x] Xây dựng thanh công cụ phía trên cây: Ô tìm kiếm (Search Input), nút "Mở tất cả" và nút "Thu gọn tất cả"
- [x] Triển khai logic tìm kiếm realtime: Lọc nhanh các nhánh chứa từ khóa và tự động mở các nhánh khớp kết quả
- [x] Xử lý trạng thái không tìm thấy kết quả (Empty/No Results State) hiển thị thông báo thân thiện
- [x] Triển khai nút "Mở tất cả" (Expand All): Mở bung toàn bộ các nhánh trong cây
- [x] Triển khai nút "Thu gọn tất cả" (Collapse All): Đóng tất cả về trạng thái gốc
- [x] Kiểm tra và định dạng an toàn cho các nội dung chứa ký tự đặc biệt, bảng Markdown, hoặc khối code nhiều dòng

---

## Phase 6: Local Run Instructions (Hướng dẫn Chạy Local)
- [x] Cập nhật `README.md` với hướng dẫn mở trực tiếp file `index.html` bằng trình duyệt
- [x] Bổ sung lệnh chạy local server bằng Python (`python -m http.server 3000`)
- [x] Bổ sung lệnh chạy local server bằng Node/npx (`npx serve .`)
- [x] Ghi rõ địa chỉ truy cập local (`http://localhost:3000`) và cách mở Developer Tools kiểm tra lỗi
- [x] Bổ sung mục xử lý sự cố thường gặp (Troubleshooting) nếu file dữ liệu không nạp được

---

## Phase 7: ngrok Demo Setup (Chuẩn bị Demo qua ngrok)
- [x] Bổ sung hướng dẫn cài đặt và cấu hình authtoken cho ngrok vào `README.md`
- [x] Thêm lệnh mở tunnel cho cổng local (`ngrok http 3000`)
- [x] Xây dựng kịch bản demo mẫu (Demo Script): thứ tự các bước thao tác duyệt cây, mở bài học, xem code, tìm kiếm để trình bày mượt mà
- [x] Kiểm tra thực tế liên kết public URL từ ngrok trên thiết bị khác (điện thoại hoặc máy tính khác)
