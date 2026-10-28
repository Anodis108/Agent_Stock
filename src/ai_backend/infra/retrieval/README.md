# Retrieval Infrastructure (`ai_backend.infra.retrieval`)

Package này map với module **`app/retrieval/`** trong giáo trình `llm-engineer-demo`.

## Vai trò kiến trúc

Cung cấp khả năng tìm kiếm ngữ nghĩa và truy xuất tài liệu khái niệm (RAG - Retrieval-Augmented Generation) cho hệ thống Multi-Agent:

- **`concepts.py`**:
  - Đọc và phân đoạn các tài liệu markdown khái niệm tài chính tại `resources/docs/concepts/`.
  - Sinh vector embeddings (OpenAI `text-embedding-3-small` hoặc local fallback hash vector khi chạy offline/test).
  - Khởi tạo và đồng bộ collection `stock_concepts` trên cơ sở dữ liệu vector Qdrant.
- **`answer.py`**:
  - Truy vấn tìm kiếm top-k đoạn văn bản có độ tương đồng cosine cao nhất với câu hỏi người dùng.
  - Áp dụng ngưỡng liên quan tối thiểu (`min_relevance`), trả về đoạn trích dẫn và nguồn tài liệu (`source_file`).
  - Nếu độ tương đồng không đạt ngưỡng, trả về hằng số chuẩn `NOT_IN_DOCS` ("Không có trong tài liệu.") để tránh hallucination.

## Ánh xạ tương thích

- `ai_backend.infra.retrieval` là package chuẩn mới (canonical).
- `ai_backend.infra.qdrant` đóng vai trò facade/alias tương thích ngược cho các module và bài kiểm thử hiện hữu.
