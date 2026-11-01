/**
 * Cây Kiến Thức LLM Engineer Handbook
 * Data Store: Knowledge Base trích xuất từ 00-gioi-thieu.md và 3 Modules
 * Auto-generated & formatted for Spec-Driven Development (Phase 3)
 */

const KNOWLEDGE_DATA = {
  "metadata": {
    "title": "LLM Engineer Handbook",
    "subtitle": "Cây Kiến Thức Tương Tác",
    "version": "1.0.0",
    "totalModules": 3,
    "totalLessons": 25,
    "totalTopics": 167
  },
  "modules": [
    {
      "id": "module-intro",
      "title": "Giới thiệu & Lộ trình tổng thể",
      "badge": "Tổng quan",
      "icon": "🧭",
      "lessons": [
        {
          "id": "intro-l1",
          "title": "Tổng quan Khoá học LLM Engineer",
          "badge": "2 mục",
          "topics": [
            {
              "id": "intro-l1-t1",
              "title": "Mục tiêu & Cấu trúc 3 Module",
              "lead": "Khoá học LLM Engineer trang bị toàn bộ kỹ năng cần thiết để xây dựng các hệ thống AI thực tế từ nền tảng đến production.",
              "concept": "Khoá học LLM Engineer trang bị toàn bộ kỹ năng cần thiết để xây dựng các hệ thống AI thực tế: gọi API, chạy model local, fine-tuning, RAG pipeline, Agentic RAG, và đánh giá hệ thống.\n\nCấu trúc gồm 3 Module:\n- Module I: LLM, Prompt, RAG & Vector DB (9 bài)\n- Module II: AI Agent & Multi-Agent Systems (8 bài)\n- Module III: Production LLMOps (8 bài)",
              "codeLang": "markdown",
              "code": "| Module | Chủ đề | Nội dung chính |\n| --- | --- | --- |\n| Module I | LLM, Prompt, RAG & Vector DB | APIs, Local LLMs, Fine-tuning, Embeddings, RAG, Evaluation |\n| Module II | AI Agent | LangGraph, Memory, Tool Design, Multi-Agent |\n| Module III | Production LLMOps | Evaluation Pipelines, Cost, Docker, Cloud, CI/CD, Observability |",
              "tip": "Mỗi bài học được thiết kế độc lập — bạn có thể đọc tuần tự hoặc tra cứu trực tiếp theo nhu cầu dự án."
            },
            {
              "id": "intro-l1-t2",
              "title": "Phương pháp học & Tài nguyên",
              "lead": "Hướng dẫn khai thác tài liệu, thực hành code mẫu và tiếp cận theo quy trình kỹ sư AI.",
              "concept": "- Mỗi bài được thiết kế độc lập, có mục lục tra cứu nhanh.\n- Kết hợp song song giữa lý thuyết kiến trúc và code thực hành chạy được ngay.\n- Tích hợp các dự án Capstone thực tế: Trợ lý pháp lý tiếng Việt, Multi-Agent Research Assistant, Production LLM Serving.",
              "codeLang": "bash",
              "code": "# Cài đặt môi trường học tập cơ bản\npip install openai langchain langgraph chromadb pydantic fastapi uvicorn",
              "tip": "Thực hành ngay mã nguồn sau mỗi bài học để nắm vững các trường hợp edge case trong production."
            }
          ]
        }
      ]
    },
    {
      "id": "module-1",
      "title": "Module I: LLM, Prompt, RAG & Vector DB",
      "badge": "9 bài",
      "icon": "📦",
      "lessons": [
        {
          "id": "module-1-l1",
          "title": "Bài 1: LLM APIs Hands-on",
          "badge": "8 mục",
          "topics": [
            {
              "id": "module-1-l1-t1",
              "title": "1. Chat Completions",
              "lead": "Mọi LLM API (OpenAI, Anthropic, Gemini, v.v.) đều xoay quanh một endpoint chính: chat completions — nhận vào một danh sách messages, trả về message của assistant.",
              "concept": "",
              "codeLang": "python",
              "code": "from openai import OpenAI\n\nclient = OpenAI()\n\nresponse = client.chat.completions.create(\n    model=\"gpt-4o-mini\",\n    messages=[\n        {\"role\": \"system\", \"content\": \"Bạn là trợ lý hữu ích.\"},\n        {\"role\": \"user\", \"content\": \"Giải thích RAG trong 2 câu.\"}\n    ]\n)\n\nprint(response.choices[0].message.content)",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-1-l1-t2",
              "title": "2. Parameters Quan Trọng",
              "lead": "Kiểm soát mức độ ngẫu nhiên trong output.",
              "concept": "| Giá trị | Hành vi |\n| --- | --- |\n| `1.0` | Xét toàn bộ phân phối (mặc định) |\n| `0.9` | Cân bằng — loại bỏ các token đuôi xác suất thấp |\n| `0.1–0.3` | Rất tập trung, gần như deterministic |\n> **Không nên chỉnh đồng thời temperature và top_p.** Cả hai đều kiểm soát tính ngẫu nhiên theo cơ chế khác nhau. Khuyến nghị chỉ chỉnh **một** trong hai, giữ cái còn lại ở giá trị mặc định để tránh tương tác khó dự đoán.\n### Các parameters khác\n| Parameter | Mô tả | Giá trị phổ biến |\n| --- | --- | --- |\n| `frequency_penalty` | Phạt token xuất hiện nhiều lần → giảm lặp | `0.0–1.0` |\n| `presence_penalty` | Khuyến khích model đề cập chủ đề mới | `0.0–1.0` |\n| `seed` | Cố định kết quả (hỗ trợ reproducibility) | Bất kỳ integer |",
              "codeLang": "python",
              "code": "response = client.chat.completions.create(\n    model=\"gpt-4o-mini\",\n    messages=[{\"role\": \"user\", \"content\": \"Tóm tắt RAG.\"}],\n    temperature=0.2,\n    max_tokens=150,\n)",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-1-l1-t3",
              "title": "3. Streaming",
              "lead": "Thay vì đợi toàn bộ response, streaming trả về token theo thời gian thực — trải nghiệm người dùng tốt hơn nhiều.",
              "concept": "Thay vì đợi toàn bộ response, streaming trả về token theo thời gian thực — trải nghiệm người dùng tốt hơn nhiều.\n\n**Khi nào dùng streaming:** Chat interfaces (hiển thị text ngay khi có), response dài (> 500 tokens), cần first-token latency thấp.",
              "codeLang": "python",
              "code": "stream = client.chat.completions.create(\n    model=\"gpt-4o-mini\",\n    messages=[{\"role\": \"user\", \"content\": \"Kể một câu chuyện ngắn.\"}],\n    stream=True,\n)\n\nfor chunk in stream:\n    if chunk.choices[0].delta.content:\n        print(chunk.choices[0].delta.content, end=\"\", flush=True)",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-1-l1-t4",
              "title": "4. Rate Limits & API Key Rotation",
              "lead": "Mọi LLM provider đều giới hạn số lượng request để bảo vệ hạ tầng. Khi vượt ngưỡng, API trả về lỗi HTTP 429 (Too Many Requests).",
              "concept": "> **Tôn trọng header ****`Retry-After`****.** Nhiều provider trả về header `Retry-After` (số giây nên đợi) trong response 429. Ưu tiên dùng giá trị này thay vì tự tính backoff khi có.\n### API Key Rotation\nKhi cần throughput vượt limit của một key, có thể luân phiên (rotate) qua nhiều API key — mỗi key có hạn mức riêng.\n\nRotation nâng cao — tự động loại key đang bị rate limit:\n\n> **Bảo mật API key:** Luôn đọc key từ biến môi trường (`os.environ`) hoặc secrets manager, không hardcode. Không commit key lên git (thêm `.env` vào `.gitignore`). Rotation chỉ là giải pháp tạm thời — nếu cần throughput cao ổn định, hãy yêu cầu provider nâng tier hoặc dùng batch API.",
              "codeLang": "python",
              "code": "import time\nimport random\nfrom openai import OpenAI, RateLimitError\n\nclient = OpenAI()\n\ndef chat_with_retry(messages, max_retries=5):\n    for attempt in range(max_retries):\n        try:\n            return client.chat.completions.create(\n                model=\"gpt-4o-mini\",\n                messages=messages,\n            )\n        except RateLimitError:\n            if attempt == max_retries - 1:\n                raise\n            # Exponential backoff: 1s, 2s, 4s, 8s... + jitter\n            wait = (2 ** attempt) + random.uniform(0, 1)\n            print(f\"Rate limited. Đợi {wait:.1f}s rồi thử lại...\")\n            time.sleep(wait)",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-1-l1-t5",
              "title": "5. Prompt Patterns",
              "lead": "Không cung cấp ví dụ — chỉ mô tả task.",
              "concept": "**Phù hợp khi:** Task đơn giản, rõ ràng; model đã được train trên task tương tự.\n### Few-shot Prompting\nCung cấp 2–5 ví dụ (input → output) trước khi đưa ra câu hỏi thực.\n\n**Phù hợp khi:** Task có format output cụ thể; cần định hướng tone/style cho model.\n> **Chọn examples tốt:** Examples nên đa dạng, bao phủ các edge case. Thứ tự examples ảnh hưởng đến kết quả — ví dụ gần nhất thường có trọng số cao hơn.\n### Chain-of-Thought (CoT)\nYêu cầu model \"suy nghĩ từng bước\" trước khi đưa ra câu trả lời. Cải thiện đáng kể độ chính xác trên các task đòi hỏi lý luận.\n**Zero-shot CoT:**\n\n**Few-shot CoT:**",
              "codeLang": "python",
              "code": "**Phù hợp khi:** Task đơn giản, rõ ràng; model đã được train trên task tương tự.\n### Few-shot Prompting\nCung cấp 2–5 ví dụ (input → output) trước khi đưa ra câu hỏi thực.",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-1-l1-t6",
              "title": "6. Structured Outputs với Pydantic",
              "lead": "LLM mặc định trả về text tự do — khó parse, không đáng tin cậy về format. Structured outputs đảm bảo output luôn theo schema định trước.",
              "concept": "**Lợi ích:** Không cần regex parsing hay try/except JSON; schema được enforce ở model level; type-safe — IDE hỗ trợ autocomplete.",
              "codeLang": "python",
              "code": "from pydantic import BaseModel\nfrom openai import OpenAI\n\nclass ProductReview(BaseModel):\n    sentiment: str          # \"positive\" | \"negative\" | \"neutral\"\n    score: int              # 1-5\n    key_points: list[str]   # Các điểm chính\n    summary: str            # Tóm tắt ngắn\n\nclient = OpenAI()\n\nreview_text = \"Pin trâu, camera đẹp nhưng giá hơi cao so với phân khúc.\"\n\ncompletion = client.beta.chat.completions.parse(\n    model=\"gpt-4o-mini\",\n    messages=[\n        {\"role\": \"system\", \"content\": \"Phân tích review sản phẩm.\"},\n        {\"role\": \"user\", \"content\": review_text}\n    ],\n    response_format=ProductReview,\n)\n\nresult = completion.choices[0].message.parsed\nprint(result.sentiment)    # \"neutral\"\nprint(result.score)        # 3\nprint(result.key_points)   # [\"pin trâu\", \"camera đẹp\", \"giá cao\"]",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-1-l1-t7",
              "title": "7. Function Calling",
              "lead": "Function calling cho phép model \"quyết định\" gọi function nào với arguments nào — model không thực thi function, chỉ trả về JSON mô tả lời gọi. Code của bạn thực thi rồi trả kết quả về.",
              "concept": "**Ứng dụng phổ biến của Function Calling:** Tìm kiếm web/database; đặt lịch, gửi email, tạo ticket; tính toán/gọi API bên ngoài; xây dựng AI agents.",
              "codeLang": "python",
              "code": "### Ví dụ: Tra thời tiết",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-1-l1-t8",
              "title": "Tóm tắt Bài 1",
              "lead": "mermaid",
              "concept": "| Kỹ thuật | Khi nào dùng |\n| --- | --- |\n| Zero-shot | Task đơn giản, rõ ràng |\n| Few-shot | Cần format / tone cụ thể |\n| CoT | Reasoning, toán, logic |\n| Role prompting | Domain-specific, kiểm soát persona |\n| Structured outputs | Pipeline cần parse output |\n| Function calling | Cần tương tác với hệ thống bên ngoài |",
              "codeLang": "mermaid",
              "code": "graph TD\n    A[LLM API Request] --> B{Loại task?}\n    B -->|Output tự do| C[Điều chỉnh Temperature]\n    B -->|Output có cấu trúc| D[Structured Outputs + Pydantic]\n    B -->|Cần dữ liệu bên ngoài| E[Function Calling]\n    C --> F{Độ phức tạp?}\n    F -->|Đơn giản| G[Zero-shot]\n    F -->|Cần format cụ thể| H[Few-shot]\n    F -->|Cần lý luận| I[Chain-of-Thought]\n    F -->|Cần domain expertise| J[Role Prompting]",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            }
          ]
        },
        {
          "id": "module-1-l2",
          "title": "Bài 2: Local LLMs",
          "badge": "2 mục",
          "topics": [
            {
              "id": "module-1-l2-t1",
              "title": "Phần A — Kiến trúc LLM",
              "lead": " Hiểu bên trong một Large Language Model: từ cơ chế Attention đến quy trình huấn luyện Pre-train và Post-train.",
              "concept": "> Hiểu bên trong một Large Language Model: từ cơ chế Attention đến quy trình huấn luyện Pre-train và Post-train.\n### 1. Attention Mechanism\n#### Vấn đề Attention giải quyết\nTrước Attention, RNN/LSTM xử lý token tuần tự — thông tin từ đầu câu dần \"mờ nhạt\" khi câu dài. Attention cho phép model nhìn trực tiếp đến **bất kỳ vị trí nào** trong sequence, bất kể khoảng cách.\n\n**Giải thích từng bước:**\n\n#### Multi-Head Attention\nThay vì 1 Attention, dùng **H heads song song** — mỗi head học một loại quan hệ khác nhau.",
              "codeLang": "python",
              "code": "#### Scaled Dot-Product Attention\nMỗi token được biểu diễn bằng 3 vector:\n| Vector | Ký hiệu | Ý nghĩa |\n| --- | --- | --- |\n| **Query** | Q | \"Tôi đang tìm kiếm thông tin gì?\" |\n| **Key** | K | \"Tôi chứa thông tin gì?\" |\n| **Value** | V | \"Nội dung thực tế tôi mang theo\" |",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-1-l2-t2",
              "title": "Phần B — Serving Local LLMs",
              "lead": "Chạy LLM trên máy local hoặc server riêng mang lại kiểm soát hoàn toàn về privacy, chi phí và latency. Phần này gồm landscape open-source, kỹ thuật quantization, và cách serve model với Ollama.",
              "concept": "Chạy LLM trên máy local hoặc server riêng mang lại kiểm soát hoàn toàn về privacy, chi phí và latency. Phần này gồm landscape open-source, kỹ thuật quantization, và cách serve model với Ollama.\n### 1. Open-source LLM Landscape\n#### Các dòng model chính\n| Dòng model | Tổ chức | Điểm mạnh |\n| --- | --- | --- |\n| **Llama 3.x** | Meta | Hiệu năng tốt, cộng đồng lớn, permissive license |\n| **Qwen 2.5 / 3** | Alibaba | Đa ngôn ngữ, code, math xuất sắc |\n| **Gemma 3** | Google | Nhẹ, chạy tốt trên GPU yếu |\n| **Mistral / Mixtral** | Mistral AI | MoE architecture, hiệu quả compute |\n| **Phi-4** | Microsoft | Small model, reasoning mạnh |\n| **DeepSeek-R1** | DeepSeek | Reasoning, math, code cực mạnh |\n#### Vietnamese LLMs\n| Model | Base | Ghi chú |\n| --- | --- | --- |\n| **Vistral-7B-Chat** | Mistral 7B | Fine-tuned tiếng Việt bởi Viet-Mistral team |\n| **PhoGPT** | GPT-J | Model tiếng Việt từ VinAI Research |\n| **SeaLLM** | Llama 2 | Đa ngôn ngữ Đông Nam Á, bao gồm tiếng Việt |\n| **Qwen2.5 (multilingual)** | Qwen 2.5 | Hỗ trợ tiếng Việt tốt trong các model đa ngôn ngữ |\n> **Lựa chọn model cho tiếng Việt:** Năm 2026, các model đa ngôn ngữ lớn như Qwen 2.5 và Llama 3.x thường cho chất lượng tiếng Việt tốt hơn các model tiếng Việt chuyên biệt kích thước nhỏ hơn, nhờ training data phong phú hơn.\n### 2. Quantization\n#### Vấn đề\nModel full precision (FP32) cực kỳ nặng:\n- Llama 3 8B FP32 ≈ **32 GB** VRAM\n- Llama 3 8B FP16 ≈ **16 GB** VRAM\n- Llama 3 8B INT4 ≈ **4–5 GB** VRAM ✅ (chạy được trên RTX 3060 12GB)\nQuantization giảm số bit để biểu diễn mỗi weight → giảm VRAM, tăng tốc inference.\n#### Các loại Precision\n\n| Precision | VRAM (8B model) | Chất lượng | Dùng khi |\n| --- | --- | --- | --- |\n| FP32 | ~32 GB | Baseline | Training research |\n| BF16/FP16 | ~16 GB | ≈ FP32 | Training, serving GPU mạnh |\n| INT8 | ~8 GB | -1 đến -2% | Production server |\n| INT4 | ~4 GB | -3 đến -5% | Consumer GPU, local |\n#### Các Format Quantization\n**GGUF (llama.cpp):**\n\n**GPTQ:**",
              "codeLang": "python",
              "code": "| Precision | VRAM (8B model) | Chất lượng | Dùng khi |\n| --- | --- | --- | --- |\n| FP32 | ~32 GB | Baseline | Training research |\n| BF16/FP16 | ~16 GB | ≈ FP32 | Training, serving GPU mạnh |\n| INT8 | ~8 GB | -1 đến -2% | Production server |\n| INT4 | ~4 GB | -3 đến -5% | Consumer GPU, local |\n#### Các Format Quantization\n**GGUF (llama.cpp):**",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            }
          ]
        },
        {
          "id": "module-1-l3",
          "title": "Bài 3: Fine-tuning với LoRA/QLoRA",
          "badge": "7 mục",
          "topics": [
            {
              "id": "module-1-l3-t1",
              "title": "1. Decision Framework: Prompt vs RAG vs Fine-tuning",
              "lead": "Đây là câu hỏi quan trọng nhất trước khi đầu tư vào fine-tuning.",
              "concept": "Đây là câu hỏi quan trọng nhất trước khi đầu tư vào fine-tuning.",
              "codeLang": "mermaid",
              "code": "graph TD\n    START[Vấn đề của bạn?] --> Q1{Model cần kiến thức từ tài liệu cụ thể?}\n    Q1 -->|Có| RAG[→ RAG Pipeline]\n    Q1 -->|Không| Q2{Model cần thay đổi hành vi / style / format?}\n    Q2 -->|Có thể làm với prompting| PROMPT[→ Prompt Engineering]\n    Q2 -->|Không đủ| Q3{Có đủ training data? ≥ 1000 examples}\n    Q3 -->|Có| FINETUNE[→ Fine-tuning]\n    Q3 -->|Không| SYNTHETIC[→ Tạo synthetic data rồi fine-tune]",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-1-l3-t2",
              "title": "2. Full Fine-tuning vs PEFT",
              "lead": "Update toàn bộ parameters của model.",
              "concept": "**Vấn đề:** Llama 3 8B (~8B params × 2 bytes FP16) = **16 GB** chỉ cho weights; optimizer states (AdamW) chiếm thêm 2× weights = **+32 GB**; gradient checkpointing **+8 GB** → tổng **~56 GB VRAM** — cần nhiều A100 80GB.\n### PEFT (Parameter-Efficient Fine-Tuning)\nChỉ train **một phần nhỏ** parameters mới được thêm vào, giữ nguyên weights gốc.\n\n| Phương pháp | % Params Trainable | Memory | Chất lượng |\n| --- | --- | --- | --- |\n| Full FT | 100% | ~56 GB (8B) | Tốt nhất |\n| LoRA | ~0.5–2% | ~6–12 GB | Gần bằng Full FT |\n| QLoRA | ~0.5–2% | ~4–6 GB | Tốt (nhỏ hơn LoRA) |\n| Prompt Tuning | <0.01% | Rất thấp | Thấp hơn |",
              "codeLang": "python",
              "code": "# Tất cả weights đều được cập nhật\nfor param in model.parameters():\n    param.requires_grad = True  # Tất cả đều train",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-1-l3-t3",
              "title": "3. LoRA - Low-Rank Adaptation",
              "lead": "LoRA giả định rằng \"knowledge updates\" trong fine-tuning có rank thấp — tức là có thể biểu diễn bằng tích hai ma trận nhỏ.",
              "concept": "Với `r = 8` và `d = 4096` (Llama 7B):\n\n**Chọn r như thế nào:** `r=8` (task đơn giản, ít data); `r=16` (balanced, phổ biến nhất); `r=32–64` (task phức tạp, nhiều data; cần nhiều VRAM hơn).",
              "codeLang": "python",
              "code": "Với `r = 8` và `d = 4096` (Llama 7B):",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-1-l3-t4",
              "title": "4. QLoRA - Quantized LoRA",
              "lead": "QLoRA kết hợp quantization (4-bit) + LoRA: (1) Load model ở 4-bit NF4, (2) Thêm LoRA adapters ở FP16/BF16, (3) Chỉ train LoRA adapters.",
              "concept": "QLoRA kết hợp quantization (4-bit) + LoRA: (1) Load model ở **4-bit NF4**, (2) Thêm LoRA adapters ở **FP16/BF16**, (3) Chỉ train LoRA adapters.",
              "codeLang": "python",
              "code": "",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-1-l3-t5",
              "title": "5. Fine-tuning Llama 3.2 3B với TRL SFTTrainer",
              "lead": "python",
              "concept": "### Full Training Script",
              "codeLang": "python",
              "code": "# Mỗi example có 3 trường\n{\n    \"instruction\": \"Dịch câu sau sang tiếng Anh.\",\n    \"input\": \"Hôm nay trời đẹp quá.\",\n    \"output\": \"The weather is so beautiful today.\"\n}",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-1-l3-t6",
              "title": "6. Merge Adapter & Push lên HF Hub",
              "lead": "python",
              "concept": "",
              "codeLang": "python",
              "code": "from peft import PeftModel\nfrom transformers import AutoModelForCausalLM, AutoTokenizer\n\n# Load base model (full precision)\nbase_model = AutoModelForCausalLM.from_pretrained(\n    \"meta-llama/Llama-3.2-3B-Instruct\",\n    torch_dtype=torch.float16,\n    device_map=\"auto\",\n)\n\n# Load và merge adapter\nmodel = PeftModel.from_pretrained(base_model, \"./llama-3.2-3b-alpaca-vi\")\nmodel = model.merge_and_unload()   # ← Merge vào base weights\n\nprint(\"Merged! Model sẵn sàng để deploy.\")",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-1-l3-t7",
              "title": "Tóm tắt Bài 3",
              "lead": "| Khái niệm | Key Points |",
              "concept": "| Khái niệm | Key Points |\n| --- | --- |\n| **Decision Framework** | Thử Prompt → RAG → Fine-tune theo thứ tự chi phí tăng dần |\n| **LoRA** | Thêm 2 ma trận nhỏ (A, B) cho mỗi weight; chỉ train A và B |\n| **QLoRA** | LoRA + 4-bit quantization → train 8B model trên GPU 24GB |\n| **r (rank)** | Cao hơn = nhiều params hơn = chất lượng cao hơn = chậm hơn |\n| **lora_alpha** | Thường = 2×r; ảnh hưởng đến tốc độ học |\n| **Merge** | `merge_and_unload()` → single model không cần PEFT khi inference |\n> **Pitfalls phổ biến:**\n> 1. **Catastrophic forgetting** — fine-tune quá nhiều epoch → model quên kiến thức gốc → dùng `r` nhỏ hơn hoặc epoch ít hơn.\n> 2. **Data quality > quantity** — 500 examples chất lượng cao tốt hơn 5000 examples kém.\n> 3. **Learning rate quá cao** — 2e-4 là điểm khởi đầu tốt; quá cao sẽ phá vỡ model.",
              "codeLang": "text",
              "code": "",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            }
          ]
        },
        {
          "id": "module-1-l4",
          "title": "Bài 4: Embeddings & Vector Databases",
          "badge": "5 mục",
          "topics": [
            {
              "id": "module-1-l4-t1",
              "title": "1. Embeddings",
              "lead": "Embedding là quá trình ánh xạ text → vector trong không gian nhiều chiều, sao cho các text có nghĩa tương đồng thì vector gần nhau.",
              "concept": "",
              "codeLang": "python",
              "code": "### Sentence-transformers",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-1-l4-t2",
              "title": "2. Similarity Metrics",
              "lead": "Đo góc giữa 2 vectors — không phụ thuộc vào magnitude (độ dài vector).",
              "concept": "**Dùng khi:** Embedding không được normalize theo magnitude — muốn so sánh hướng, không phải độ lớn.\n### Dot Product\n\n**Dùng khi:** Vectors đã được L2-normalized (hầu hết embedding models modern). Nhanh hơn cosine.\n### Euclidean Distance\n\n**Dùng khi:** Magnitude quan trọng; ít dùng trong NLP hơn cosine/dot.\n| Metric | Khi nào dùng | Lưu ý |\n| --- | --- | --- |\n| Cosine | Default choice cho text | Normalize trước nếu chưa normalize |\n| Dot Product | Vectors đã L2-normalized | Nhanh nhất |\n| Euclidean | Khi magnitude có ý nghĩa | Ít dùng cho NLP |",
              "codeLang": "python",
              "code": "",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-1-l4-t3",
              "title": "3. Approximate Nearest Neighbor (ANN)",
              "lead": "Tìm kiếm chính xác (brute-force) trong 1 triệu vectors 768 chiều: quá chậm cho production. ANN hi sinh một chút accuracy để đổi lấy tốc độ tìm kiếm.",
              "concept": "**Đặc điểm HNSW:** Rất nhanh (sub-millisecond với hàng triệu vectors); RAM-based → cần load vào memory; phù hợp Chroma, Qdrant, Weaviate.\n### IVF - Inverted File Index\nChia vectors thành các **clusters** (Voronoi cells). Khi tìm kiếm, chỉ search trong `nprobe` clusters gần nhất.\n\n**Đặc điểm IVF:** Disk-friendly — phù hợp dataset rất lớn (billions of vectors); cần tune `nlist` (số clusters) và `nprobe`; phù hợp FAISS, pgvector.",
              "codeLang": "python",
              "code": "### HNSW - Hierarchical Navigable Small World\nHNSW xây dựng đồ thị phân cấp: lớp trên ít nodes (highway), lớp dưới nhiều nodes (local roads).",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-1-l4-t4",
              "title": "4. Vector Databases",
              "lead": "| DB | Index | Deployment | Ưu điểm | Nhược điểm |",
              "concept": "",
              "codeLang": "python",
              "code": "import chromadb\nfrom sentence_transformers import SentenceTransformer\n\nclient = chromadb.PersistentClient(path=\"./chroma_db\")\ncollection = client.get_or_create_collection(\n    name=\"legal_docs\",\n    metadata={\"hnsw:space\": \"cosine\"}\n)\n\nmodel = SentenceTransformer(\"intfloat/multilingual-e5-large\")\n\ndocuments = [\n    \"Điều 14 Luật Doanh nghiệp: Công ty TNHH có từ 2 đến 50 thành viên.\",\n    \"Điều 46: Thành viên góp vốn chịu trách nhiệm trong phạm vi vốn góp.\",\n]\n\nembeddings = model.encode(documents).tolist()\n\ncollection.add(\n    ids=[\"doc_1\", \"doc_2\"],\n    embeddings=embeddings,\n    documents=documents,\n    metadatas=[{\"source\": \"luat-dn-2020\", \"dieu\": \"14\"},\n               {\"source\": \"luat-dn-2020\", \"dieu\": \"46\"}],\n)\n\nquery = \"Số lượng thành viên tối đa của công ty TNHH?\"\nquery_embedding = model.encode([query]).tolist()\n\nresults = collection.query(\n    query_embeddings=query_embedding,\n    n_results=3,\n    where={\"source\": \"luat-dn-2020\"},\n)\n\nfor doc, meta, dist in zip(\n    results[\"documents\"][0],\n    results[\"metadatas\"][0],\n    results[\"distances\"][0]\n):\n    print(f\"[{dist:.3f}] {doc[:80]}...\")",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-1-l4-t5",
              "title": "Tóm tắt: Chọn Vector DB cho dự án",
              "lead": "mermaid",
              "concept": "| Tình huống | Khuyến nghị |\n| --- | --- |\n| Prototype nhanh | Chroma |\n| Production self-hosted | Qdrant |\n| Đã có PostgreSQL stack | pgvector |\n| Cần scale tự động | Pinecone |\n| Tiếng Việt, open-source embedding | `BAAI/bge-m3` hoặc `multilingual-e5-large` |",
              "codeLang": "mermaid",
              "code": "graph TD\n    A{Quy mô?} -->|Dev / POC| B[Chroma - đơn giản nhất]\n    A -->|< 10M vectors, self-hosted| C[Qdrant - cân bằng tốt]\n    A -->|Đã dùng PostgreSQL| D[pgvector - tiện tích hợp]\n    A -->|Serverless, không muốn ops| E[Pinecone - managed]\n    A -->|Research, cần speed tối đa| F[FAISS - fastest]",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            }
          ]
        },
        {
          "id": "module-1-l5",
          "title": "Bài 5: RAG Pipeline",
          "badge": "6 mục",
          "topics": [
            {
              "id": "module-1-l5-t1",
              "title": "1. Kiến trúc Tổng quan RAG",
              "lead": "mermaid",
              "concept": "",
              "codeLang": "mermaid",
              "code": "graph LR\n    subgraph Ingestion [Ingestion - Chạy 1 lần]\n        D[Documents PDF/DOCX/HTML] --> L[Loader]\n        L --> C[Chunking]\n        C --> E[Embedding Model]\n        E --> V[(Vector DB)]\n    end\n    subgraph Inference [Inference - Mỗi query]\n        Q[User Query] --> QE[Embed Query]\n        QE --> S[Semantic Search]\n        V --> S\n        S --> R[Ranked Chunks]\n        R --> P[Augmented Prompt]\n        P --> LLM[LLM]\n        LLM --> A[Answer + Citations]\n    end",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-1-l5-t2",
              "title": "2. Ingestion Pipeline",
              "lead": "python",
              "concept": "**Document object:**\n\n**Ưu điểm:** Đơn giản, dự đoán được **Nhược điểm:** Có thể cắt giữa câu/đoạn\n**Semantic Chunking:**\n\n**Ưu điểm:** Chunks có nghĩa hoàn chỉnh hơn **Nhược điểm:** Chậm hơn, chi phí embedding cao hơn\n**Markdown / Structure-aware:**",
              "codeLang": "python",
              "code": "from langchain_community.document_loaders import (\n    PyPDFLoader, Docx2txtLoader, UnstructuredHTMLLoader, DirectoryLoader,\n)\n\n# PDF\nloader = PyPDFLoader(\"luat-doanh-nghiep-2020.pdf\")\npages = loader.load()  # List[Document], mỗi Document là 1 trang\n\n# DOCX\nloader = Docx2txtLoader(\"hop-dong.docx\")\ndocs = loader.load()\n\n# Toàn bộ thư mục\nloader = DirectoryLoader(\n    \"./legal_docs/\",\n    glob=\"**/*.pdf\",\n    loader_cls=PyPDFLoader,\n    show_progress=True,\n)\nall_docs = loader.load()",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-1-l5-t3",
              "title": "3. Retrieval",
              "lead": "python",
              "concept": "**Khi nào dùng Hybrid Search:**\n- Documents chứa nhiều proper nouns, số liệu, mã điều luật\n- Queries ngắn, keyword-based\n- Cần cả precision (keyword) và recall (semantic)\n### Re-ranking",
              "codeLang": "python",
              "code": "retriever = vectorstore.as_retriever(search_type=\"similarity\", search_kwargs={\"k\": 5})\nresults = retriever.invoke(\"Điều kiện thành lập công ty TNHH là gì?\")",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-1-l5-t4",
              "title": "4. Generation",
              "lead": "python",
              "concept": "",
              "codeLang": "python",
              "code": "rag_prompt = ChatPromptTemplate.from_template(\"\"\"\nBạn là trợ lý pháp lý chuyên về luật doanh nghiệp Việt Nam.\nChỉ trả lời dựa trên TÀI LIỆU được cung cấp bên dưới.\nNếu thông tin không có trong tài liệu, hãy nói rõ \"Thông tin này không có trong tài liệu\".\n\nTÀI LIỆU:\n{context}\n\nCÂU HỎI: {question}\n\nTrả lời bằng tiếng Việt, trích dẫn điều khoản cụ thể khi có thể:\"\"\")",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-1-l5-t5",
              "title": "5. Full RAG Pipeline - Chat với Vietnamese PDFs",
              "lead": "python",
              "concept": "",
              "codeLang": "python",
              "code": "from langchain_community.document_loaders import PyPDFDirectoryLoader\nfrom langchain_text_splitters import RecursiveCharacterTextSplitter\nfrom langchain_community.embeddings import HuggingFaceEmbeddings\nfrom langchain_community.vectorstores import Chroma\nfrom langchain_openai import ChatOpenAI\nfrom langchain_core.prompts import ChatPromptTemplate\nfrom langchain_core.runnables import RunnablePassthrough\nfrom langchain_core.output_parsers import StrOutputParser\n\n# ====== INGESTION ======\nloader = PyPDFDirectoryLoader(\"./legal_pdfs/\")\ndocs = loader.load()\nsplitter = RecursiveCharacterTextSplitter(chunk_size=512, chunk_overlap=64)\nchunks = splitter.split_documents(docs)\n\nembedding = HuggingFaceEmbeddings(\n    model_name=\"intfloat/multilingual-e5-large\",\n    encode_kwargs={\"normalize_embeddings\": True},\n)\nvectorstore = Chroma.from_documents(chunks, embedding, persist_directory=\"./db\")\nretriever = vectorstore.as_retriever(search_kwargs={\"k\": 5})\n\n# ====== RETRIEVAL & GENERATION ======\nprompt = ChatPromptTemplate.from_template(\"\"\"\nTrả lời câu hỏi dựa trên tài liệu pháp lý sau.\nNếu không có thông tin, nói rõ \"Không tìm thấy thông tin\".\n\nTài liệu: {context}\n\nCâu hỏi: {question}\"\"\")\n\nllm = ChatOpenAI(model=\"gpt-4o-mini\", temperature=0)\n\nrag_chain = (\n    {\"context\": retriever | (lambda docs: \"\\n\\n\".join(d.page_content for d in docs)),\n     \"question\": RunnablePassthrough()}\n    | prompt | llm | StrOutputParser()\n)\n\nanswer = rag_chain.invoke(\"Điều kiện thành lập công ty TNHH theo luật 2",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-1-l5-t6",
              "title": "Tóm tắt: Các quyết định quan trọng",
              "lead": "| Bước | Lựa chọn | Khuyến nghị |",
              "concept": "| Bước | Lựa chọn | Khuyến nghị |\n| --- | --- | --- |\n| **Loader** | PyPDF, Unstructured, LlamaParse | PyPDF cho PDF đơn giản; LlamaParse cho PDF phức tạp |\n| **Chunk size** | 256–1024 chars | 512 chars + 64 overlap là điểm khởi đầu tốt |\n| **Embedding** | OpenAI / BGE-M3 / multilingual-e5 | BGE-M3 cho tiếng Việt self-hosted |\n| **Retrieval** | Semantic / Hybrid | Hybrid khi có proper nouns / mã số |\n| **Re-ranking** | Cross-encoder | Thêm vào khi precision không đủ |\n| **top_k** | 3–10 | Bắt đầu với 5; tăng nếu cần nhiều context hơn |\n> **Debugging RAG** — Khi RAG không hoạt động tốt, debug theo thứ tự:\n> 1. **Retrieval** — retrieved chunks có relevant không? (`retriever.invoke(query)`)\n> 2. **Chunking** — chunk có đủ context không? Thử tăng `chunk_size`\n> 3. **Embedding model** — thử model khác, check similarity scores\n> 4. **Prompt** — model có bị \"lạc lối\" không? Thêm constraint rõ hơn",
              "codeLang": "text",
              "code": "",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            }
          ]
        },
        {
          "id": "module-1-l6",
          "title": "Bài 6: Agentic RAG",
          "badge": "6 mục",
          "topics": [
            {
              "id": "module-1-l6-t1",
              "title": "1. Giới hạn của RAG Truyền thống",
              "lead": "| Vấn đề | Mô tả | Ví dụ |",
              "concept": "| Vấn đề | Mô tả | Ví dụ |\n| --- | --- | --- |\n| **Always retrieves** | Retrieve ngay cả khi không cần | \"2 + 2 = ?\" vẫn search vector DB |\n| **No quality check** | Không kiểm tra chunks có relevant không | Trả về nonsense nếu không có thông tin |\n| **Single-hop** | Không thể chain nhiều retrieval steps | Câu hỏi cần info từ 2 tài liệu khác nhau |\n| **No fallback** | Không có plan B khi không tìm được | Hallucinate thay vì từ chối |",
              "codeLang": "text",
              "code": "",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-1-l6-t2",
              "title": "2. Self-RAG",
              "lead": "Self-RAG thêm reflection tokens vào quá trình generation — model tự đánh giá ở mỗi bước.",
              "concept": "Self-RAG thêm **reflection tokens** vào quá trình generation — model tự đánh giá ở mỗi bước.\n\n**Chunk relevance** — Chunk có liên quan không?\n\n**Answer faithfulness** — Câu trả lời có dựa trên tài liệu không?",
              "codeLang": "mermaid",
              "code": "graph LR\n    Q[Query] --> R1{Retrieve?}\n    R1 -->|Yes| RETRIEVE[Retrieve Chunks]\n    R1 -->|No| GENERATE[Generate Directly]\n    RETRIEVE --> R2{Chunk Relevant?}\n    R2 -->|Relevant| GENERATE\n    R2 -->|Irrelevant| SKIP[Skip chunk]\n    GENERATE --> R3{Answer Faithful?}\n    R3 -->|Faithful| OUTPUT[Final Answer]\n    R3 -->|Not faithful| RETRY[Retry or abstain]",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-1-l6-t3",
              "title": "3. Corrective RAG (CRAG)",
              "lead": "CRAG là phiên bản practical hơn của Self-RAG với grading + fallback to web search.",
              "concept": "CRAG là phiên bản practical hơn của Self-RAG với **grading + fallback to web search**.",
              "codeLang": "mermaid",
              "code": "graph TD\n    Q[User Query] --> RETRIEVE[Retrieve from Vector DB]\n    RETRIEVE --> GRADE[Grade Each Chunk]\n    GRADE --> DECISION{Quality?}\n    DECISION -->|All relevant| GENERATE[Generate Answer]\n    DECISION -->|Mixed / Ambiguous| REFINE[Refine Knowledge + Web Search]\n    DECISION -->|All irrelevant| WEB[Web Search Fallback]\n    REFINE --> GENERATE\n    WEB --> GENERATE\n    GENERATE --> OUTPUT[Final Answer]",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-1-l6-t4",
              "title": "4. Query Decomposition & Multi-hop",
              "lead": "Câu hỏi phức tạp cần thông tin từ nhiều nguồn hoặc nhiều bước suy luận:",
              "concept": "Câu hỏi phức tạp cần thông tin từ nhiều nguồn hoặc nhiều bước suy luận:\n\nCần decompose thành:",
              "codeLang": "python",
              "code": "Cần decompose thành:",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-1-l6-t5",
              "title": "5. LangGraph Basics",
              "lead": "LangGraph cho phép xây dựng stateful multi-step workflows cho LLM.",
              "concept": "LangGraph cho phép xây dựng **stateful multi-step workflows** cho LLM.\n**State:** TypedDict chứa toàn bộ thông tin của workflow\n\n**Nodes:** Functions nhận state → trả về partial state update\n\n**Edges:** Kết nối các nodes (static hoặc conditional)",
              "codeLang": "python",
              "code": "class AgentState(TypedDict):\n    messages: list          # Conversation history\n    documents: list         # Retrieved documents\n    iterations: int         # Số lần retry\n    final_answer: str       # Kết quả cuối",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-1-l6-t6",
              "title": "Tóm tắt: Chọn RAG Pattern",
              "lead": "| Pattern | Phù hợp khi | Độ phức tạp |",
              "concept": "| Pattern | Phù hợp khi | Độ phức tạp |\n| --- | --- | --- |\n| **Basic RAG** | Query đơn giản, corpus nhỏ | ⭐ |\n| **Self-RAG** | Cần kiểm soát retrieval necessity | ⭐⭐⭐ |\n| **CRAG** | Corpus không đầy đủ, cần fallback | ⭐⭐ |\n| **Query Decomposition** | Câu hỏi phức tạp, multi-aspect | ⭐⭐ |\n| **Multi-hop** | Câu hỏi cần chain nhiều retrieval | ⭐⭐⭐ |\n> **Bắt đầu đơn giản:** Luôn bắt đầu với Basic RAG, đo lường chất lượng với RAGAS, sau đó thêm complexity khi cần. CRAG là điểm nâng cấp phổ biến nhất.",
              "codeLang": "text",
              "code": "",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            }
          ]
        },
        {
          "id": "module-1-l7",
          "title": "Bài 7: LLM Evaluation & Guardrails",
          "badge": "5 mục",
          "topics": [
            {
              "id": "module-1-l7-t1",
              "title": "1. LLM Evaluation",
              "lead": "BLEU — đo n-gram overlap giữa output và reference:",
              "concept": "**ROUGE** — recall-oriented, tốt cho summarization:\n\n**Giới hạn Classic Metrics:** Chỉ đo lexical overlap, không hiểu semantic meaning.\n### BERTScore",
              "codeLang": "python",
              "code": "from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction\n\nreference = [[\"Công\", \"ty\", \"TNHH\", \"có\", \"tối\", \"đa\", \"50\", \"thành\", \"viên\"]]\nhypothesis = [\"Công\", \"ty\", \"TNHH\", \"được\", \"phép\", \"có\", \"50\", \"thành\", \"viên\"]\n\nscore = sentence_bleu(reference, hypothesis, smoothing_function=SmoothingFunction().method1)\n# → 0.61 (đo n-gram overlap)",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-1-l7-t2",
              "title": "2. RAG Evaluation với RAGAS",
              "lead": "| Metric | Đo gì | Cần ground truth? | Range |",
              "concept": "| Metric | Đo gì | Cần ground truth? | Range |\n| --- | --- | --- | --- |\n| **Faithfulness** | % claims trong answer được support bởi context | Không | 0–1 |\n| **Answer Relevancy** | Answer có liên quan đến question không | Không | 0–1 |\n| **Context Recall** | Context có chứa đủ info để trả lời không | Có | 0–1 |\n| **Context Precision** | Retrieved chunks có relevant không | Có | 0–1 |\n### Implementation",
              "codeLang": "python",
              "code": "from ragas import evaluate\nfrom ragas.metrics import (\n    faithfulness,\n    answer_relevancy,\n    context_recall,\n    context_precision,\n)\nfrom datasets import Dataset\n\n# Chuẩn bị test dataset\ntest_data = {\n    \"question\": [\n        \"Công ty TNHH có thể có tối đa bao nhiêu thành viên?\",\n        \"Điều kiện để trở thành thành viên góp vốn là gì?\",\n    ],\n    \"answer\": [          # Generated answers\n        \"Theo Điều 46 Luật Doanh nghiệp 2020, công ty TNHH có từ 2 đến 50 thành viên.\",\n        \"Thành viên góp vốn phải đáp ứng điều kiện về năng lực pháp lý...\",\n    ],\n    \"contexts\": [        # Retrieved chunks (list of lists)\n        [\"Điều 46: Công ty trách nhiệm hữu hạn có từ 2 đến 50 thành viên...\"],\n        [\"Điều 47: Thành viên công ty...\"],\n    ],\n    \"ground_truth\": [    # Reference answers (cho context_recall)\n        \"Tối đa 50 thành viên\",\n        \"Phải có năng lực hành vi dân sự đầy đủ...\",\n    ],\n}\n\ndataset = Dataset.from_dict(test_data)\n\nresults = evaluate(\n    dataset=dataset,\n    metrics=[faithfulness, answer_relevancy, context_recall, context_precision],\n    llm=ChatOpenAI(model=\"gpt-4o-mini\"),\n)\n\nprint(results)\n# {'faithfulness': 0.92, 'answer_relevancy': 0.88,\n#  'context_recall': 0.85, 'context_precision': 0.79}",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-1-l7-t3",
              "title": "3. Guardrails",
              "lead": "Kẻ tấn công cố nhúng instructions vào user input để override system prompt:",
              "concept": "**Phòng thủ:**",
              "codeLang": "python",
              "code": "**Phòng thủ:**",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-1-l7-t4",
              "title": "4. Monitoring với LangSmith / LangFuse",
              "lead": "python",
              "concept": "",
              "codeLang": "python",
              "code": "import os\nos.environ[\"LANGCHAIN_TRACING_V2\"] = \"true\"\nos.environ[\"LANGCHAIN_API_KEY\"] = \"ls__...\"\nos.environ[\"LANGCHAIN_PROJECT\"] = \"vietnamese-legal-rag\"\n# Sau đó mọi LangChain call đều được trace tự động",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-1-l7-t5",
              "title": "Tóm tắt Bài 7",
              "lead": "| Component | Tool | Khi nào dùng |",
              "concept": "| Component | Tool | Khi nào dùng |\n| --- | --- | --- |\n| **Classic metrics** | BLEU, ROUGE | Benchmark nhanh, không tốn phí |\n| **Semantic metrics** | BERTScore | Khi paraphrase quan trọng |\n| **RAG eval** | RAGAS | Đánh giá cả retrieval + generation |\n| **LLM judge** | GPT-4o-mini | Evaluation phức tạp, cần reasoning |\n| **Injection defense** | Regex + LLM check | Luôn dùng trong production |\n| **PII filtering** | Presidio + Regex | Khi xử lý thông tin người dùng |\n| **Monitoring** | LangSmith / LangFuse | Production - theo dõi chất lượng |\n> **Evaluation Checklist trước khi deploy:**\n> - Faithfulness > 0.85 trên test set\n> - Answer Relevancy > 0.85\n> - Prompt injection test pass\n> - PII không leak trong responses\n> - Latency p95 < 5s\n> - Monitoring dashboard đã setup",
              "codeLang": "text",
              "code": "",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            }
          ]
        },
        {
          "id": "module-1-l8",
          "title": "Bài 8: Production Optimization — Latency & Cost",
          "badge": "5 mục",
          "topics": [
            {
              "id": "module-1-l8-t1",
              "title": "1. Bức tranh chi phí & độ trễ",
              "lead": "mermaid",
              "concept": "| Kỹ thuật | Giảm gì | Cơ chế |\n| --- | --- | --- |\n| **Prompt Caching** | Cost input + TTFT | Cache phần prefix lặp lại của prompt |\n| **Semantic Caching** | Cost + latency toàn bộ | Trả lại câu trả lời cũ cho câu hỏi tương tự |\n| **Model Routing** | Cost + latency | Gửi task dễ tới model rẻ, task khó tới model mạnh |",
              "codeLang": "mermaid",
              "code": "graph LR\n    REQ[Request] --> C1{Đã thấy prefix này?}\n    C1 -->|Có| PC[Prompt Cache - giảm cost input]\n    C1 -->|Chưa| C2{Câu hỏi tương tự đã hỏi?}\n    C2 -->|Có| SC[Semantic Cache - bỏ qua LLM hoàn toàn]\n    C2 -->|Chưa| C3{Task khó hay dễ?}\n    C3 -->|Dễ| SMALL[Model nhỏ/rẻ]\n    C3 -->|Khó| BIG[Model lớn/mạnh]",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-1-l8-t2",
              "title": "2. Prompt Caching",
              "lead": "Khi nhiều request chia sẻ chung một prefix dài (system prompt, few-shot examples, tài liệu context), provider có thể cache phần đã xử lý này và tái sử dụng - không tính lại từ đầu.",
              "concept": "**OpenAI (automatic caching):**\n\n> **Nguyên tắc vàng: tĩnh trước, động sau.** Prompt caching chỉ hit khi **prefix khớp chính xác**.",
              "codeLang": "python",
              "code": "### Lợi ích\n- **Giảm cost**: token cache thường rẻ hơn 50–90% so với token thường.\n- **Giảm TTFT** (Time To First Token): không phải xử lý lại prefix.\n### Cách dùng\n**Anthropic (explicit caching):**",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-1-l8-t3",
              "title": "3. Semantic Caching",
              "lead": "Prompt caching yêu cầu prefix khớp y hệt. Semantic caching đi xa hơn: nếu một câu hỏi gần giống về ngữ nghĩa với câu đã hỏi trước, ta trả lại câu trả lời cũ — bỏ qua LLM hoàn toàn.",
              "concept": "Prompt caching yêu cầu prefix **khớp y hệt**. Semantic caching đi xa hơn: nếu một câu hỏi **gần giống về ngữ nghĩa** với câu đã hỏi trước, ta trả lại câu trả lời cũ — **bỏ qua LLM hoàn toàn**.\n\n> **Cẩn trọng với threshold và tính tươi của dữ liệu:**\n> - **Threshold quá thấp** → trả nhầm câu trả lời cho câu hỏi khác nghĩa (false positive nguy hiểm).\n> - **Threshold quá cao** → ít cache hit, mất tác dụng.\n> - Không hợp cho câu trả lời phụ thuộc thời gian/ngữ cảnh (\"Hôm nay thế nào?\", giá cổ phiếu...). Cần đặt **TTL** để invalidate cache cũ.\n>\n> Production thường dùng vector store chuyên dụng (Redis với RediSearch, hoặc thư viện GPTCache) thay cho list in-memory.",
              "codeLang": "python",
              "code": "### Kiến trúc",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-1-l8-t4",
              "title": "4. Model Routing",
              "lead": "Không phải request nào cũng cần model mạnh nhất. \"1 + 1 bằng mấy?\" không cần tới model flagship đắt tiền.",
              "concept": "Không phải request nào cũng cần model mạnh nhất. \"1 + 1 bằng mấy?\" không cần tới model flagship đắt tiền.\n\n> **Router phải nhẹ hơn cái nó định tuyến:** Một router lý tưởng phải **nhanh và rẻ hơn nhiều** so với chính các model nó định tuyến tới. Nếu router tốn bằng việc gọi model lớn thì vô nghĩa.\n### 4.1. Rule-based Routing\n\" in query:\n        return \"gpt-4o\"\n\nreturn \"gpt-4o-mini\"  # mặc định\npython\nfrom sentence_transformers import SentenceTransformer\nimport numpy as np",
              "codeLang": "python",
              "code": "> **Router phải nhẹ hơn cái nó định tuyến:** Một router lý tưởng phải **nhanh và rẻ hơn nhiều** so với chính các model nó định tuyến tới. Nếu router tốn bằng việc gọi model lớn thì vô nghĩa.\n### 4.1. Rule-based Routing",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-1-l8-t5",
              "title": "Tóm tắt Bài 8",
              "lead": "mermaid",
              "concept": "| Kỹ thuật | Khi nào dùng |\n| --- | --- |\n| Prompt Caching | Prompt có prefix dài lặp lại (system prompt, RAG context) |\n| Semantic Caching | Nhiều câu hỏi trùng/gần giống nhau (FAQ, support bot) |\n| Rule-based Routing | Domain hẹp, pattern rõ ràng, cần baseline nhanh |\n| Embedding Routing | Cần hiểu ngữ nghĩa, chưa có training data |\n| Classifier Routing | Volume lớn, chênh lệch cost cao, tối ưu nghiêm túc |",
              "codeLang": "mermaid",
              "code": "graph TD\n    REQ[Incoming Request] --> PC[1. Prompt Caching - tĩnh trước, động sau]\n    PC --> SC[2. Semantic Cache - check câu tương tự]\n    SC -->|HIT| DONE[Trả lời ngay]\n    SC -->|MISS| ROUTE[3. Model Routing]\n    ROUTE -->|Dễ| SMALL[Model nhỏ/rẻ]\n    ROUTE -->|Khó| BIG[Model lớn/mạnh]\n    SMALL --> DONE\n    BIG --> DONE",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            }
          ]
        },
        {
          "id": "module-1-l9",
          "title": "Bài 9: Capstone Project — Vietnamese Legal Assistant",
          "badge": "8 mục",
          "topics": [
            {
              "id": "module-1-l9-t1",
              "title": "Kiến trúc Hệ thống",
              "lead": "mermaid",
              "concept": "",
              "codeLang": "mermaid",
              "code": "graph TD\n    subgraph Ingestion\n        PDF[Vietnamese Legal PDFs] --> LOAD[Document Loader]\n        LOAD --> CHUNK[Chunking 512 chars, 64 overlap]\n        CHUNK --> EMBED[multilingual-e5-large]\n        EMBED --> VDB[(Qdrant / Chroma)]\n    end\n    subgraph CRAG Agent - LangGraph\n        Q[User Query] --> GUARD_IN[Input Guardrails - PII + Injection]\n        GUARD_IN --> RETRIEVE[Retrieve Top-10]\n        VDB --> RETRIEVE\n        RETRIEVE --> GRADE[Grade Chunks - LLM-as-judge]\n        GRADE --> DECIDE{Quality?}\n        DECIDE -->|Good| GEN[Generate Answer]\n        DECIDE -->|Poor| WEB[Tavily Web Search]\n        WEB --> GEN\n        GEN --> GUARD_OUT[Output Guardrails - Faithfulness check]\n        GUARD_OUT --> CITE[Add Citations]\n    end\n    subgraph Presentation\n        CITE --> UI[Gradio UI]\n        UI --> DEPLOY[HF Spaces]\n    end",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-1-l9-t2",
              "title": "1. Ingestion Pipeline",
              "lead": "python",
              "concept": "",
              "codeLang": "python",
              "code": "import os\nfrom pathlib import Path\nfrom langchain_community.document_loaders import PyPDFDirectoryLoader\nfrom langchain_text_splitters import RecursiveCharacterTextSplitter\nfrom langchain_community.embeddings import HuggingFaceEmbeddings\nfrom langchain_community.vectorstores import Chroma\n\ndef build_ingestion_pipeline(pdf_dir: str, persist_dir: str):\n    \"\"\"\n    Ingestion pipeline cho Vietnamese legal PDFs.\n\n    Args:\n        pdf_dir: Thư mục chứa PDFs\n        persist_dir: Nơi lưu vector store\n    \"\"\"\n    print(f\"📄 Loading PDFs from {pdf_dir}...\")\n    loader = PyPDFDirectoryLoader(pdf_dir, glob=\"**/*.pdf\")\n    docs = loader.load()\n    print(f\"✅ Loaded {len(docs)} pages from {len(set(d.metadata['source'] for d in docs))} files\")\n\n    # Chunking\n    print(\"✂️ Chunking documents...\")\n    splitter = RecursiveCharacterTextSplitter(\n        chunk_size=512,\n        chunk_overlap=64,\n        separators=[\"\\n\\n\", \"\\n\", \".\", \" \"],\n    )\n    chunks = splitter.split_documents(docs)\n\n    # Enrich metadata\n    for chunk in chunks:\n        chunk.metadata[\"chunk_size\"] = len(chunk.page_content)\n        source = Path(chunk.metadata[\"source\"]).stem\n        chunk.metadata[\"law_name\"] = source\n\n    print(f\"✅ Created {len(chunks)} chunks\")\n\n    # Embedding & indexing\n    print(\"🔢 Embedding and indexing...\")\n    embedding = HuggingFaceEmbeddings(\n        model_name=\"intfloat/multilingual-e5-large\",\n        encode_kwargs={\"normalize_embeddings\": True},\n    )\n\n    vectorstore = Chroma.from_documents(",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-1-l9-t3",
              "title": "2. CRAG Agent với LangGraph",
              "lead": "python",
              "concept": "",
              "codeLang": "python",
              "code": "from typing import TypedDict\nfrom langgraph.graph import StateGraph, END\nfrom langchain_openai import ChatOpenAI\nfrom langchain_core.prompts import ChatPromptTemplate\nfrom langchain_community.tools.tavily_search import TavilySearchResults\nimport json\n\n# ====== STATE ======\nclass LegalAgentState(TypedDict):\n    question: str\n    documents: list\n    generation: str\n    web_search: bool\n    citations: list\n    guardrail_passed: bool\n\n# ====== LLM + TOOLS ======\nllm = ChatOpenAI(model=\"gpt-4o-mini\", temperature=0.1)\nweb_search = TavilySearchResults(max_results=3)\nretriever = vectorstore.as_retriever(search_kwargs={\"k\": 10})\n\n# ====== PROMPTS ======\nGRADE_PROMPT = \"\"\"Đánh giá xem TÀI LIỆU có liên quan đến CÂU HỎI pháp lý không.\n\nCâu hỏi: {question}\nTài liệu: {document}\n\nTrả về JSON: {{\"relevant\": true/false, \"score\": 0.0-1.0}}\"\"\"\n\nRAG_PROMPT = \"\"\"Bạn là chuyên gia pháp lý Việt Nam. Trả lời câu hỏi DỰA TRÊN TÀI LIỆU.\nNếu không có thông tin, nói rõ \"Không tìm thấy thông tin trong tài liệu hiện có\".\nTrích dẫn điều khoản cụ thể khi có thể.\n\nTài liệu:\n{context}\n\nCâu hỏi: {question}\n\nCâu trả lời:\"\"\"\n\n# ====== NODES ======\ndef retrieve(state: LegalAgentState):\n    docs = retriever.invoke(state[\"question\"])\n    return {\"documents\": docs, \"web_search\": False}\n\ndef grade_documents(state: LegalAgentState):\n    relevant_docs = []\n    web_search_needed = False\n\n    for doc in state[\"documents\"]:\n        try:\n            result = llm.invoke(GRADE_PROMPT.format(\n                question=state[\"q",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-1-l9-t4",
              "title": "3. Guardrails Integration",
              "lead": "python",
              "concept": "",
              "codeLang": "python",
              "code": "import re\n\ndef input_guardrails(question):\n    injection_patterns = [r\"ignore.*(instruction|system|prompt)\", r\"bỏ qua.*hướng dẫn\", r\"you are now\", r\"act as\"]\n    for pattern in injection_patterns:\n        if re.search(pattern, question.lower()):\n            return False, \"Phát hiện prompt injection\"\n    if len(question) > 2000:\n        return False, \"Câu hỏi quá dài (tối đa 2000 ký tự)\"\n    if len(question.strip()) < 5:\n        return False, \"Câu hỏi quá ngắn\"\n    return True, \"OK\"\n\ndef run_agent_with_guardrails(question):\n    passed, reason = input_guardrails(question)\n    if not passed:\n        return {\"answer\": f\"⚠️ {reason}\", \"citations\": [], \"web_used\": False}\n    result = legal_agent.invoke({\"question\": question})\n    _, clean_answer = output_guardrails(result[\"generation\"])\n    return {\"answer\": clean_answer, \"citations\": result.get(\"citations\", []), \"web_used\": result.get(\"web_search\", False)}",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-1-l9-t5",
              "title": "4. Gradio UI",
              "lead": "python",
              "concept": "",
              "codeLang": "python",
              "code": "import gradio as gr\n\ndef chat_interface(question, history):\n    result = run_agent_with_guardrails(question)\n    answer = result[\"answer\"]\n    if result[\"citations\"]:\n        sources = list(set([f\"{c['source']} tr.{c['page']}\" for c in result[\"citations\"]]))\n        answer += f\"\\n\\n📚 *Nguồn: {', '.join(sources[:3])}*\"\n    if result[\"web_used\"]:\n        answer += \"\\n\\n🌐 *Một phần thông tin từ tìm kiếm web*\"\n    history.append((question, answer))\n    return \"\", history\n\nwith gr.Blocks(title=\"Trợ lý Pháp lý Việt Nam\", theme=gr.themes.Soft()) as demo:\n    gr.Markdown(\"\"\"\n    # ⚖️ Trợ lý Pháp lý Việt Nam\n    Đặt câu hỏi về luật doanh nghiệp, luật lao động và các văn bản pháp luật Việt Nam.\n    > ⚠️ Đây là công cụ tham khảo, không thay thế tư vấn pháp lý chính thức.\n    \"\"\")\n    chatbot = gr.Chatbot(height=500, show_label=False)\n    with gr.Row():\n        msg = gr.Textbox(placeholder=\"Nhập câu hỏi pháp lý của bạn...\", show_label=False, scale=9)\n        submit = gr.Button(\"Gửi\", scale=1, variant=\"primary\")\n    examples = gr.Examples(\n        examples=[\"Điều kiện thành lập công ty TNHH 2 thành viên?\",\n                   \"Người lao động có quyền nghỉ phép năm bao nhiêu ngày?\",\n                   \"Thủ tục đăng ký kinh doanh hộ cá thể?\"],\n        inputs=msg,\n    )\n    submit.click(chat_interface, [msg, chatbot], [msg, chatbot])\n    msg.submit(chat_interface, [msg, chatbot], [msg, chatbot])\ndemo.launch(share=True)",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-1-l9-t6",
              "title": "5. Deploy lên HF Spaces",
              "lead": "yaml",
              "concept": "",
              "codeLang": "yaml",
              "code": "# README.md header cho HF Spaces\n---\ntitle: Vietnamese Legal Assistant\nemoji: ⚖️\ncolorFrom: blue\ncolorTo: indigo\nsdk: gradio\nsdk_version: 4.x\napp_file: app.py\npinned: false\n---",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-1-l9-t7",
              "title": "6. RAGAS Evaluation — Take-home",
              "lead": "python",
              "concept": "",
              "codeLang": "python",
              "code": "from ragas import evaluate\nfrom ragas.metrics import faithfulness, answer_relevancy, context_recall, context_precision\n\nresults = []\nfor q in test_questions:\n    agent_result = legal_agent.invoke({\"question\": q})\n    results.append({\"question\": q, \"answer\": agent_result[\"generation\"],\n        \"contexts\": [d.page_content for d in agent_result[\"documents\"]]})\n\neval_dataset = Dataset.from_list(results)\nscores = evaluate(dataset=eval_dataset,\n    metrics=[faithfulness, answer_relevancy, context_recall, context_precision])",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-1-l9-t8",
              "title": "Checklist Hoàn thiện Dự án",
              "lead": "- [ ] Ingestion pipeline xử lý được ≥ 5 PDFs pháp lý tiếng Việt",
              "concept": "- [ ] Ingestion pipeline xử lý được ≥ 5 PDFs pháp lý tiếng Việt\n- [ ] CRAG agent chạy được với LangGraph\n- [ ] Web search fallback hoạt động\n- [ ] Input/output guardrails active\n- [ ] Gradio UI với chat history và citations\n- [ ] Deploy thành công lên HF Spaces\n- [ ] RAGAS evaluation với 30 Q&A pairs, tất cả 4 metrics\n- [ ] Faithfulness \\> 0.80 trên test set\n---\n*Tổng hợp từ YourClass Handbook — LLM Engineer (Module I, II & III). Nội dung phục vụ học tập & tra cứu nội bộ.*",
              "codeLang": "text",
              "code": "",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            }
          ]
        }
      ]
    },
    {
      "id": "module-2",
      "title": "Module II: AI Agent",
      "badge": "8 bài",
      "icon": "🤖",
      "lessons": [
        {
          "id": "module-2-l1",
          "title": "Bài 1: What Is an AI Agent?",
          "badge": "9 mục",
          "topics": [
            {
              "id": "module-2-l1-t1",
              "title": "Tổng quan",
              "lead": "Bài này xây dựng nền tảng khái niệm cho toàn bộ Module II: agent là gì, khác gì với một lời gọi LLM đơn thuần hay một RAG pipeline cố định, các thành phần cấu thành nên một agent, cách cấu trúc system prompt cho agent phức tạp, và bức tranh",
              "concept": "Bài này xây dựng nền tảng khái niệm cho toàn bộ Module II: agent là gì, khác gì với một lời gọi LLM đơn thuần hay một RAG pipeline cố định, các thành phần cấu thành nên một agent, cách cấu trúc system prompt cho agent phức tạp, và bức tranh landscape framework/protocol năm 2026.",
              "codeLang": "text",
              "code": "",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-2-l1-t2",
              "title": "1. Định nghĩa & Sự tiến hoá",
              "lead": "Một AI agent là một hệ thống dùng LLM làm bộ não trung tâm để tự quyết định chuỗi hành động cần thực hiện nhằm đạt mục tiêu, thay vì đi theo một luồng xử lý cố định do lập trình viên viết sẵn.",
              "concept": "A2A là gì?\n**Agent2Agent (A2A)** là chuẩn giao tiếp giữa các agent với nhau (agent-to-agent), khác với MCP vốn chuẩn hoá giao tiếp giữa agent và tool/data source. A2A liên quan trực tiếp đến Multi-Agent Systems ([Bài 6](https://handbook.yourclassacademy.com/llm-engineer/module-2/06-multi-agent/)) nhưng nằm ngoài phạm vi module này - chỉ nhắc đến ở đây để định vị trong bức tranh landscape.",
              "codeLang": "mermaid",
              "code": "graph LR\n    A[2020-2022<br/>Prompt engineering<br/>1 lời gọi, output cố định] --> B[2023<br/>ReAct, Chain-of-Thought<br/>Reasoning + Action]\n    B --> C[2024<br/>Function calling chuẩn hoá<br/>LangChain, AutoGPT]\n    C --> D[2025<br/>Graph-based orchestration<br/>LangGraph, CrewAI, OpenAI Agents SDK]\n    D --> E[2026<br/>Protocol chuẩn hoá<br/>MCP, A2A, Multi-agent phổ biến]",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-2-l1-t3",
              "title": "2. Core Components",
              "lead": "Mọi agent, dù dùng framework nào, đều gồm 4 thành phần:",
              "concept": "Mọi agent, dù dùng framework nào, đều gồm 4 thành phần:\n\n| Thành phần | Vai trò | Ví dụ |\n| --- | --- | --- |\n| **LLM Brain** | Reasoning, ra quyết định, chọn hành động tiếp theo | GPT-4o, Claude, Gemini |\n| **Tools** | Cầu nối với thế giới bên ngoài | Web search, database query, RAG retrieval, code execution |\n| **Memory** | Giữ ngữ cảnh qua nhiều bước / nhiều lượt hội thoại | Conversation history, vector store, scratchpad |\n| **Planning Loop** | Vòng lặp quan sát - suy nghĩ - hành động, quyết định khi nào dừng | ReAct loop, task decomposition |\nThiếu 1 thành phần vẫn có thể gọi là agent, nhưng giới hạn\nMột chatbot chỉ có LLM Brain + Memory (không có Tools) chỉ có thể trò chuyện, không thể hành động. Một script gọi tool cố định (không có Planning Loop) là automation, không phải agent thực sự.",
              "codeLang": "mermaid",
              "code": "graph TD\n    subgraph Agent\n        BRAIN[LLM Brain<br/>Reasoning + Decision making]\n        TOOLS[Tools<br/>Function calling, APIs, RAG]\n        MEMORY[Memory<br/>Short-term + Long-term]\n        PLAN[Planning Loop<br/>Observe → Think → Act]\n    end\n    BRAIN <--> TOOLS\n    BRAIN <--> MEMORY\n    BRAIN --> PLAN\n    PLAN --> BRAIN",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-2-l1-t4",
              "title": "3. System Prompt: Cấu trúc & Cách lắp ráp",
              "lead": "System prompt là nơi cấu hình \"LLM Brain\" - agent càng phức tạp, system prompt càng cần được lắp ráp có cấu trúc thay vì viết tay một đoạn văn dài.",
              "concept": "System prompt là nơi cấu hình \"LLM Brain\" - agent càng phức tạp, system prompt càng cần được **lắp ráp có cấu trúc** thay vì viết tay một đoạn văn dài.\n### 6 tầng của một system prompt\n| Tầng | Trả lời câu hỏi | Ví dụ |\n| --- | --- | --- |\n| **Identity** | Agent là ai? | \"Bạn là trợ lý kỹ thuật cấp cao chuyên về...\" |\n| **Constraints** | Luôn/không bao giờ làm gì? | \"Không bao giờ thực thi lệnh phá huỷ dữ liệu mà chưa xác nhận\" |\n| **Capabilities** | Có tool gì? | Mô tả + schema của các tool khả dụng |\n| **Context** | Môi trường hiện tại? | Thư mục làm việc, trạng thái git, thời gian |\n| **Behavior** | Cư xử thế nào? | Tone, độ dài phản hồi, phong cách ra quyết định |\n| **Knowledge** | Kiến thức chuyên biệt? | Skill instructions, memory liên quan (Bài 3) |\n### Lắp ráp theo từng phần, không viết 1 khối văn bản\n\nAnti-pattern: nhồi tất cả vào 1 chuỗi\nViết system prompt như 1 đoạn văn dài chứa mọi thứ (identity + toàn bộ 50 tool + toàn bộ lịch sử user + 200 skill) không maintain được, không customize được theo task, và lãng phí token nghiêm trọng. Luôn lắp ráp từ các phần nhỏ, lọc theo nhu cầu hiện tại - giống cách JIT tool loading lọc tool theo task ([Bài 4](https://handbook.yourclassacademy.com/llm-engineer/module-2/04-tool-design/)).\n### [AGENTS.md](http://AGENTS.md) vs [SOUL.md](http://SOUL.md): tách \"làm gì\" khỏi \"là ai\"\nVới agent cá nhân hoá (vd: trợ lý dùng lâu dài, nhớ user qua nhiều session - Bài 3), tách system prompt thành 2 file riêng biệt giúp thay đổi tính cách mà không đụng vào logic vận hành, và ngược lại:\n| File | Trả lời | Ví dụ nội dung |\n| --- | --- | --- |\n| [**AGENTS.md**](http://AGENTS.md) | Agent \\*làm gì\\*, quy tắc vận hành | \"Dùng `web_search` cho câu hỏi thực tế. Luôn xác nhận trước khi xoá dữ liệu.\" |\n| [**SOUL.md**](http://SOUL.md) | Agent \\*cư xử ra sao\\*, tính cách | \"Trả lời trực tiếp rồi mới giải thích. Thừa nhận khi không chắc thay vì bịa.\" |\n```javascript\n# AGENTS.md (vận hành - developer sở hữu)",
              "codeLang": "python",
              "code": "def assemble_system_prompt(agent_config: dict, task: str, environment: dict) -> str:\n    sections = []\n    sections.append(agent_config[\"identity\"])       # Luôn có\n    sections.append(agent_config[\"constraints\"])     # Luôn có\n    sections.append(format_tools(select_tools(task, agent_config[\"tools\"])))  # Lọc theo task\n    sections.append(format_environment(environment)) # Động, theo runtime\n    if agent_config.get(\"soul\"):\n        sections.append(agent_config[\"soul\"])         # Behavior, xem SOUL.md bên dưới\n    return \"\\n\\n\".join(sections)",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-2-l1-t5",
              "title": "Quy tắc công cụ",
              "lead": "- Dùng searchvietnamesenews cho câu hỏi thời sự",
              "concept": "- Dùng `search_vietnamese_news` cho câu hỏi thời sự\n- Luôn xác nhận trước khi gọi tool có side effect",
              "codeLang": "text",
              "code": "",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-2-l1-t6",
              "title": "Phong cách giao tiếp",
              "lead": "- Trả lời ngắn gọn, đi thẳng vào trọng tâm",
              "concept": "- Trả lời ngắn gọn, đi thẳng vào trọng tâm\n- Dùng ví dụ cụ thể thay vì giải thích trừu tượng\n```\n**Lợi ích:** User đổi tông giọng agent ([SOUL.md](http://SOUL.md)) mà không sợ phá vỡ logic vận hành ([AGENTS.md](http://AGENTS.md)); developer thêm tool/quy tắc mới mà không ảnh hưởng tính cách đã được user tuỳ chỉnh.\nChỉ cần tách khi agent thực sự cá nhân hoá lâu dài\nVới agent dùng 1 lần hoặc task-specific (đa số ví dụ trong module này), 1 system prompt đơn giản là đủ. Tách [AGENTS.md/SOUL.md](http://AGENTS.md/SOUL.md) đáng giá khi agent phục vụ nhiều user với gu cá nhân khác nhau, hoặc khi đội ngũ vận hành và đội ngũ thiết kế trải nghiệm là 2 nhóm khác nhau.",
              "codeLang": "text",
              "code": "",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-2-l1-t7",
              "title": "4. Agent Paradigms",
              "lead": "Phản ứng trực tiếp với input hiện tại, không có bộ nhớ về quá khứ, không lập kế hoạch nhiều bước.",
              "concept": "**Phù hợp khi:** Task đơn giản, 1 bước, không cần ngữ cảnh trước đó.\n### Planning Agent\nTrước khi hành động, agent **lập kế hoạch** toàn bộ các bước cần làm, rồi thực thi theo kế hoạch (có thể điều chỉnh khi gặp lỗi).\n\n**Phù hợp khi:** Task phức tạp, nhiều bước phụ thuộc lẫn nhau, cần nhìn toàn cảnh trước khi hành động (vd: research agent trong capstone).\n### ReAct (Reasoning + Acting)\nXen kẽ giữa **suy nghĩ** (Thought), **hành động** (Action), và **quan sát** (Observation) - mỗi bước phụ thuộc vào kết quả của bước trước, thay vì lập kế hoạch toàn bộ ngay từ đầu.\n\n**Phù hợp khi:** Không biết trước cần bao nhiêu bước hoặc tool nào; mỗi bước phụ thuộc kết quả quan sát trước đó (vd: debug lỗi, multi-hop question answering).\n### So sánh 3 paradigms\n| Paradigm | Có bộ nhớ nhiều bước? | Lập kế hoạch trước? | Độ phức tạp task phù hợp |\n| --- | --- | --- | --- |\n| **Reflex** | Không | Không | Thấp - 1 bước |\n| **Planning** | Có | Có, toàn bộ trước khi chạy | Cao - nhiều bước độc lập, biết trước cấu trúc |\n| **ReAct** | Có | Không, từng bước một | Cao - nhiều bước phụ thuộc kết quả trung gian |\nLangGraph hỗ trợ cả 3 paradigm\nBài 2 sẽ dùng LangGraph để implement ReAct loop bằng state graph - đây là paradigm phổ biến nhất cho agent thực tế vì cân bằng giữa tính linh hoạt và khả năng kiểm soát.",
              "codeLang": "python",
              "code": "def reflex_agent(user_input: str) -> str:\n    # Map input → action, không suy luận nhiều bước\n    if \"thời tiết\" in user_input:\n        return get_weather()\n    if \"giá vàng\" in user_input:\n        return get_gold_price()\n    return llm_respond(user_input)",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-2-l1-t8",
              "title": "5. Landscape 2026",
              "lead": "| Framework | Điểm mạnh | Điểm yếu | Dùng khi |",
              "concept": "MCP sẽ được đào sâu ở Bài 4 (chuẩn giao tiếp, cách viết Server/Client) - phần này chỉ giới thiệu vị trí của nó trong landscape: MCP giải quyết bài toán **N agent × M tool = N×M integration** bằng cách chuẩn hoá thành **N + M**.",
              "codeLang": "mermaid",
              "code": "graph LR\n    subgraph \"Trước MCP\"\n        A1[Agent A] --> T1[Tool 1 - custom integration]\n        A1 --> T2[Tool 2 - custom integration]\n        A2[Agent B] --> T1\n        A2 --> T2\n    end",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-2-l1-t9",
              "title": "Tóm tắt",
              "lead": "mermaid",
              "concept": "| Khái niệm | Ghi nhớ |\n| --- | --- |\n| Agent vs Pipeline | Ai quyết định bước tiếp theo: code cố định hay LLM? |\n| Core components | Brain + Tools + Memory + Planning Loop |\n| System prompt | Lắp ráp từ 6 tầng, lọc theo task - không viết 1 khối văn bản |\n| [AGENTS.md](http://AGENTS.md) / [SOUL.md](http://SOUL.md) | Tách \"làm gì\" (vận hành) khỏi \"là ai\" (tính cách) |\n| Reflex | 1 bước, không nhớ, không lập kế hoạch |\n| Planning | Lập kế hoạch toàn bộ trước khi thực thi |\n| ReAct | Suy nghĩ - Hành động - Quan sát, lặp lại |\n| MCP | Chuẩn hoá kết nối agent ↔ tool, tránh N×M integration |",
              "codeLang": "mermaid",
              "code": "graph TD\n    Q{Cần xây dựng gì?} --> A[Task 1 bước, input → output cố định]\n    Q --> B[Task nhiều bước, biết trước cấu trúc]\n    Q --> C[Task nhiều bước, phụ thuộc kết quả trung gian]\n    A --> REFLEX[Reflex Agent]\n    B --> PLANNING[Planning Agent]\n    C --> REACT[ReAct Agent]\n    REACT --> FW{Framework?}\n    PLANNING --> FW\n    FW --> LG[LangGraph - kiểm soát chi tiết]\n    FW --> CREW[CrewAI - prototype nhanh]",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            }
          ]
        },
        {
          "id": "module-2-l2",
          "title": "Bài 2: Building Agents với LangGraph",
          "badge": "9 mục",
          "topics": [
            {
              "id": "module-2-l2-t1",
              "title": "Tổng quan",
              "lead": "Bài này trang bị kỹ năng xây dựng agent bằng LangGraph: biểu diễn agent như một state graph, xây dựng tool execution loop, biết khi nào dừng và phục hồi khi tool lỗi, tách biệt lập kế hoạch khỏi hành động, giữ trạng thái qua nhiều lượt hội ",
              "concept": "Bài này trang bị kỹ năng xây dựng agent bằng LangGraph: biểu diễn agent như một state graph, xây dựng tool execution loop, biết khi nào dừng và phục hồi khi tool lỗi, tách biệt lập kế hoạch khỏi hành động, giữ trạng thái qua nhiều lượt hội thoại, và chèn con người vào vòng lặp khi cần phê duyệt hành động nhạy cảm.",
              "codeLang": "text",
              "code": "",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-2-l2-t2",
              "title": "1. State, Nodes, Edges",
              "lead": "LangGraph biểu diễn agent như một đồ thị có hướng: mỗi bước xử lý là một node, luồng di chuyển giữa các bước là edge, và toàn bộ dữ liệu được chia sẻ qua các node là state.",
              "concept": "LangGraph biểu diễn agent như một **đồ thị có hướng**: mỗi bước xử lý là một **node**, luồng di chuyển giữa các bước là **edge**, và toàn bộ dữ liệu được chia sẻ qua các node là **state**.\n\n`Annotated[list, add_messages]` là gì?\nMặc định, khi một node trả về `{\"messages\": [...]}`, LangGraph sẽ **ghi đè** giá trị cũ. Dùng `add_messages` (reducer function) để thay vào đó **nối thêm** message mới vào danh sách - cần thiết để giữ lịch sử hội thoại qua nhiều bước.\n### Nodes\nNode là một hàm Python nhận `state` hiện tại, trả về phần state cần cập nhật.",
              "codeLang": "mermaid",
              "code": "graph LR\n    START((START)) --> AGENT[Agent Node]\n    AGENT -->|có tool call| TOOLS[Tool Node]\n    AGENT -->|không có tool call| END((END))\n    TOOLS --> AGENT",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-2-l2-t3",
              "title": "2. Tool Nodes & Tool Execution Loop",
              "lead": "python",
              "concept": "Đây chính là **ReAct loop** (Bài 1) được biểu diễn bằng graph: `agent → tools → agent → ... → END` cho đến khi model không còn gọi tool nữa.\nLuôn giới hạn số vòng lặp\nNếu model liên tục gọi tool (vd: do tool trả về lỗi mà model không nhận ra), graph có thể lặp vô hạn. Thêm giới hạn qua `recursion_limit` khi invoke: `app.invoke(input, config={\"recursion_limit\": 15})`.",
              "codeLang": "python",
              "code": "from langchain_core.tools import tool\n\n@tool\ndef search_vietnamese_news(query: str) -> str:\n    \"\"\"Tìm kiếm tin tức tiếng Việt mới nhất theo từ khoá.\"\"\"\n    # Gọi API thực tế ở đây\n    return f\"Kết quả tìm kiếm cho '{query}': ...\"\n\n@tool\ndef get_stock_price(symbol: str) -> str:\n    \"\"\"Lấy giá cổ phiếu hiện tại theo mã chứng khoán (vd: VNM, FPT).\"\"\"\n    return f\"{symbol}: 68,500 VNĐ (+1.2%)\"\n\ntools = [search_vietnamese_news, get_stock_price]\nllm_with_tools = llm.bind_tools(tools)",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-2-l2-t4",
              "title": "3. Loop Termination & Error Recovery",
              "lead": "Đây là câu hỏi tưởng đơn giản nhưng dễ bị bỏ qua - agent không dừng đúng lúc vừa tốn chi phí vừa có thể gây hại nếu tiếp tục hành động ngoài ý muốn.",
              "concept": "Model hiện đại tự điều chỉnh tốt khi thấy lỗi\nĐừng che giấu lỗi khỏi model bằng cách retry âm thầm hoặc trả về giá trị mặc định. Model đủ mạnh để đọc thông báo lỗi và tự thử hướng khác - đây chính là bản chất \"tự sửa lỗi\" của vòng lặp ReAct.\n### Phát hiện vòng lặp\nNếu agent lặp lại cùng 1 hành động nhiều lần liên tiếp, đó là dấu hiệu agent bị kẹt - cần can thiệp thay vì để `recursion_limit` âm thầm cắt ngang.",
              "codeLang": "python",
              "code": "@tool\ndef final_answer(answer: str) -> str:\n    \"\"\"Nộp câu trả lời cuối cùng. Chỉ gọi tool này khi đã hoàn thành nhiệm vụ.\"\"\"\n    return answer\n\ndef should_continue(state: AgentState) -> str:\n    last_message = state[\"messages\"][-1]\n    if not last_message.tool_calls:\n        return END\n    # Nếu tool call là final_answer, dừng graph dù về mặt kỹ thuật vẫn là tool call\n    if last_message.tool_calls[0][\"name\"] == \"final_answer\":\n        return END\n    return \"tools\"",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-2-l2-t5",
              "title": "4. Plan/Act Separation",
              "lead": "Lỗi phổ biến nhất của agent là lao vào hành động trước khi hiểu đủ vấn đề - sửa nhầm chỗ, edit file không cần thiết, hoặc bỏ sót ngữ cảnh quan trọng. Cline (VS Code agent) giải quyết bằng cách tách rõ 2 chế độ.",
              "concept": "Kết hợp với HITL (mục 6) - `interrupt_before` giữa 2 phase để user review kế hoạch trước khi cho phép chuyển sang Act Mode - đây là ứng dụng cụ thể của HITL cho toàn bộ 1 giai đoạn, không chỉ 1 tool call.\nTách Plan/Act là quyết định kiến trúc, không chỉ prompt\nChỉ dặn model \"hãy lập kế hoạch trước\" trong system prompt (implicit planning, Bài 1) không đủ tin cậy - model vẫn có thể lẫn lộn giữa suy nghĩ và hành động. Giới hạn **tool khả dụng theo từng node** như trên mới đảm bảo được ranh giới cứng giữa 2 giai đoạn.",
              "codeLang": "python",
              "code": "from typing import TypedDict, Annotated, Literal\nfrom langgraph.graph.message import add_messages\n\nclass PlanActState(TypedDict):\n    messages: Annotated[list, add_messages]\n    mode: Literal[\"plan\", \"act\"]\n    plan: str\n\nREAD_ONLY_TOOLS = [read_file, search_codebase, list_directory]\nALL_TOOLS = READ_ONLY_TOOLS + [edit_file, run_command, delete_file]\n\ndef plan_node(state: PlanActState) -> dict:\n    \"\"\"Chỉ dùng tool đọc - không có side effect.\"\"\"\n    llm_plan = llm.bind_tools(READ_ONLY_TOOLS)\n    response = llm_plan.invoke(\n        [{\"role\": \"system\", \"content\": \"Phân tích yêu cầu và tạo kế hoạch từng bước. \"\n                                        \"KHÔNG sửa file hay chạy lệnh - chỉ đọc và phân tích.\"}]\n        + state[\"messages\"]\n    )\n    return {\"messages\": [response]}\n\ndef act_node(state: PlanActState) -> dict:\n    \"\"\"Toàn quyền tool, chỉ chạy sau khi user duyệt plan.\"\"\"\n    llm_act = llm.bind_tools(ALL_TOOLS)\n    response = llm_act.invoke(\n        [{\"role\": \"system\", \"content\": f\"Thực thi theo kế hoạch đã duyệt:\\n{state['plan']}\"}]\n        + state[\"messages\"]\n    )\n    return {\"messages\": [response]}\n\ndef route_by_mode(state: PlanActState) -> str:\n    return \"plan\" if state[\"mode\"] == \"plan\" else \"act\"",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-2-l2-t6",
              "title": "5. Memory & State Persistence",
              "lead": "Mặc định, state chỉ tồn tại trong một lần invoke(). Để agent \"nhớ\" hội thoại qua nhiều lượt (nhiều lần gọi invoke khác nhau), dùng checkpointer.",
              "concept": "`thread_id` phân biệt các cuộc hội thoại độc lập - mỗi user/session dùng một `thread_id` riêng.\n### Persistent checkpointer cho production\n`MemorySaver` chỉ lưu trong RAM, mất khi restart. Production cần checkpointer bền vững:\n\nCheckpointer khác Memory ở Bài 3\nCheckpointer lưu **toàn bộ state của graph** (để resume/replay execution) - đây là cơ chế kỹ thuật của LangGraph. Bài 3 (Agent Memory) nói về **thiết kế những gì agent nên nhớ** (short-term, long-term, episodic...) - một bài toán ở tầng cao hơn, thường xây trên nền checkpointer này.",
              "codeLang": "python",
              "code": "from langgraph.checkpoint.memory import MemorySaver\n\ncheckpointer = MemorySaver()\napp = graph.compile(checkpointer=checkpointer)\n\nconfig = {\"configurable\": {\"thread_id\": \"user-123\"}}\n\n# Lượt 1\napp.invoke({\"messages\": [{\"role\": \"user\", \"content\": \"Tôi tên Minh.\"}]}, config=config)\n\n# Lượt 2 - agent vẫn nhớ \"Minh\" nhờ cùng thread_id\nresult = app.invoke({\"messages\": [{\"role\": \"user\", \"content\": \"Tôi tên gì?\"}]}, config=config)\nprint(result[\"messages\"][-1].content)  # \"Bạn tên Minh.\"",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-2-l2-t7",
              "title": "6. Human-in-the-Loop",
              "lead": "Với hành động nhạy cảm (xoá dữ liệu, gửi email, giao dịch tài chính), cần con người phê duyệt trước khi agent thực thi.",
              "concept": "Với hành động nhạy cảm (xoá dữ liệu, gửi email, giao dịch tài chính), cần con người phê duyệt trước khi agent thực thi.\n### Interrupt trước khi gọi tool\n\nHITL cần checkpointer\n`interrupt_before` / `interrupt_after` chỉ hoạt động khi graph được compile với checkpointer - vì graph cần lưu state tại điểm dừng để resume sau này.",
              "codeLang": "python",
              "code": "app = graph.compile(checkpointer=checkpointer, interrupt_before=[\"tools\"])\n\nconfig = {\"configurable\": {\"thread_id\": \"session-1\"}}\nresult = app.invoke(\n    {\"messages\": [{\"role\": \"user\", \"content\": \"Huỷ đơn hàng #4521 giúp tôi.\"}]},\n    config=config,\n)\n# Graph dừng lại TRƯỚC khi chạy tool node\n\n# Kiểm tra tool call agent định thực hiện\npending_call = result[\"messages\"][-1].tool_calls[0]\nprint(f\"Agent muốn gọi: {pending_call['name']}({pending_call['args']})\")\n\n# Con người phê duyệt → resume graph bằng cách invoke với input=None\nif user_approves:\n    final_result = app.invoke(None, config=config)\nelse:\n    # Từ chối: inject message huỷ bỏ rồi tiếp tục\n    pass",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-2-l2-t8",
              "title": "7. Hands-on: Vietnamese Personal Assistant",
              "lead": "Kết hợp toàn bộ: tool calling + memory + HITL cho một trợ lý cá nhân tiếng Việt.",
              "concept": "Kết hợp toàn bộ: tool calling + memory + HITL cho một trợ lý cá nhân tiếng Việt.",
              "codeLang": "python",
              "code": "from typing import TypedDict, Annotated\nfrom langgraph.graph import StateGraph, START, END\nfrom langgraph.graph.message import add_messages\nfrom langgraph.prebuilt import ToolNode\nfrom langgraph.checkpoint.memory import MemorySaver\nfrom langchain_openai import ChatOpenAI\nfrom langchain_core.tools import tool\n\n# ====== STATE ======\nclass AssistantState(TypedDict):\n    messages: Annotated[list, add_messages]\n\n# ====== TOOLS ======\n@tool\ndef check_calendar(date: str) -> str:\n    \"\"\"Kiểm tra lịch làm việc theo ngày (định dạng YYYY-MM-DD).\"\"\"\n    return f\"Ngày {date}: 14h họp team, 16h30 gọi khách hàng.\"\n\n@tool\ndef send_reminder(message: str, time: str) -> str:\n    \"\"\"Đặt lời nhắc. Hành động này cần con người phê duyệt trước khi gửi.\"\"\"\n    return f\"Đã đặt lời nhắc '{message}' lúc {time}.\"\n\n@tool\ndef search_restaurant(location: str, cuisine: str = \"\") -> str:\n    \"\"\"Tìm nhà hàng theo khu vực và loại món ăn.\"\"\"\n    return f\"3 nhà hàng {cuisine} gần {location}: Quán A, Quán B, Quán C.\"\n\ntools = [check_calendar, send_reminder, search_restaurant]\n\n# ====== LLM ======\nllm = ChatOpenAI(model=\"gpt-4o-mini\", temperature=0.2)\nllm_with_tools = llm.bind_tools(tools)\n\nSYSTEM_PROMPT = \"\"\"Bạn là trợ lý cá nhân tiếng Việt, thân thiện và ngắn gọn.\nDùng tool khi cần thông tin lịch, đặt lời nhắc, hoặc tìm nhà hàng.\"\"\"\n\n# ====== NODES ======\ndef agent_node(state: AssistantState) -> dict:\n    messages = [{\"role\": \"system\", \"content\": SYSTEM_PROMPT}] + state[\"messages\"]\n    response = llm_with_tools.i",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-2-l2-t9",
              "title": "Tóm tắt",
              "lead": "mermaid",
              "concept": "| Thành phần | Vai trò | API chính |\n| --- | --- | --- |\n| State | Dữ liệu chia sẻ giữa các node | `TypedDict`  • `Annotated[list, add_messages]` |\n| Node | Đơn vị xử lý (agent, tool) | Hàm nhận state, trả dict cập nhật |\n| Conditional edge | Rẽ nhánh dựa trên state | `add_conditional_edges` |\n| ToolNode | Tự động thực thi tool calls | `langgraph.prebuilt.ToolNode` |\n| Loop termination | Model tự dừng, max steps, explicit stop tool, goal verification | `recursion_limit`, tool `final_answer` |\n| Error recovery | Trả lỗi tool về dạng model đọc được, không raise | try/except trong tool node |\n| Plan/Act separation | Giới hạn tool theo phase để tránh hành động trước khi hiểu rõ | Node riêng + tool set riêng cho mỗi mode |\n| Checkpointer | Lưu state qua nhiều lượt invoke | `MemorySaver`, `SqliteSaver` |\n| HITL | Dừng để con người phê duyệt | `interrupt_before` / `interrupt_after` |",
              "codeLang": "mermaid",
              "code": "graph TD\n    A[Cần xây agent?] --> B[Định nghĩa State - TypedDict]\n    B --> C[Viết Agent Node - gọi LLM + tools]\n    C --> D[Viết Tool Node - ToolNode có sẵn]\n    D --> E{Cần nhớ qua nhiều lượt?}\n    E -->|Có| F[Thêm Checkpointer + thread_id]\n    E -->|Không| G[Compile graph không checkpointer]\n    F --> H{Có hành động nhạy cảm?}\n    H -->|Có| I[interrupt_before=tools]\n    H -->|Không| J[Chạy trực tiếp]",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            }
          ]
        },
        {
          "id": "module-2-l3",
          "title": "Bài 3: Agent Memory & Context Engineering",
          "badge": "7 mục",
          "topics": [
            {
              "id": "module-2-l3-t1",
              "title": "Tổng quan",
              "lead": "Context window có giới hạn, nhưng agent cần hoạt động qua hàng trăm lượt hội thoại và hàng nghìn tool call. Bài này phân loại các loại bộ nhớ agent cần, chiến lược quản lý context khi nó vượt giới hạn, cách nén thông tin mà không mất ý nghĩ",
              "concept": "Context window có giới hạn, nhưng agent cần hoạt động qua hàng trăm lượt hội thoại và hàng nghìn tool call. Bài này phân loại các loại bộ nhớ agent cần, chiến lược quản lý context khi nó vượt giới hạn, cách nén thông tin mà không mất ý nghĩa quan trọng, và **context rot** - hiện tượng chất lượng output suy giảm ngay cả khi context còn xa mới đầy.",
              "codeLang": "text",
              "code": "",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-2-l3-t2",
              "title": "1. Memory Types",
              "lead": "Con người có nhiều loại trí nhớ khác nhau cho các mục đích khác nhau - agent cũng vậy.",
              "concept": "Con người có nhiều loại trí nhớ khác nhau cho các mục đích khác nhau - agent cũng vậy.\n\n| Loại | Định nghĩa | Ví dụ | Nơi lưu trữ điển hình |\n| --- | --- | --- | --- |\n| **Short-term** | Ngữ cảnh của session/task hiện tại | Lịch sử hội thoại trong 1 conversation | Context window / state của graph |\n| **Long-term** | Thông tin tồn tại qua nhiều session | \"User tên Minh, thích nhận báo cáo dạng bullet point\" | Database / vector store |\n| **Episodic** | Ghi nhớ về các sự kiện/trải nghiệm cụ thể đã xảy ra | \"Lần trước agent gọi tool X và bị lỗi timeout\" | Log có timestamp, vector store |\n| **Semantic** | Kiến thức, sự thật chung không gắn với 1 sự kiện | \"Công ty TNHH tối đa 50 thành viên\" | Knowledge base / RAG (Module I) |\n| **Procedural** | Quy trình, cách thực hiện một loại task | \"Khi user hỏi về hoá đơn, luôn check trạng thái thanh toán trước\" | System prompt, few-shot examples, learned rules |\nEpisodic vs Semantic - phân biệt dễ nhầm\nEpisodic nhớ **\"chuyện gì đã xảy ra\"** (gắn với thời điểm cụ thể). Semantic nhớ **\"sự thật là gì\"** (không gắn thời điểm). \"Hôm qua user phàn nàn về giao hàng chậm\" là episodic. \"User ở Hà Nội\" là semantic.\n### Ánh xạ vào LangGraph\n\nLong-term/Semantic/Procedural memory thường **không** sống trong graph state - chúng được đọc từ external store (database, vector store) vào đầu session, và ghi lại (nếu cần) sau khi session kết thúc.",
              "codeLang": "mermaid",
              "code": "graph TD\n    M[Agent Memory] --> ST[Short-term<br/>Trong 1 session/task]\n    M --> LT[Long-term<br/>Xuyên suốt nhiều session]\n    LT --> EP[Episodic<br/>Sự kiện cụ thể đã xảy ra]\n    LT --> SEM[Semantic<br/>Kiến thức/sự thật chung]\n    LT --> PROC[Procedural<br/>Cách thực hiện task]",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-2-l3-t3",
              "title": "2. Management Strategies",
              "lead": "Khi hội thoại càng dài, messages trong state càng phình to → vượt context window, tăng chi phí, giảm độ chính xác (lost-in-the-middle). Cần chiến lược quản lý.",
              "concept": "Khi hội thoại càng dài, `messages` trong state càng phình to → vượt context window, tăng chi phí, giảm độ chính xác (lost-in-the-middle). Cần chiến lược quản lý.\n### Sliding Window\nChỉ giữ N message gần nhất, bỏ phần cũ hơn.\n\n**Phù hợp khi:** Hội thoại casual, thông tin cũ không còn liên quan sau vài lượt (vd: chatbot hỏi đáp đơn giản).\n**Nhược điểm:** Mất hoàn toàn thông tin bị cắt - nếu user hỏi lại điều đã nói ở đầu hội thoại dài, agent \"quên\" thật sự.\n### Summarization\nĐịnh kỳ tóm tắt phần hội thoại cũ thành 1 đoạn ngắn, thay thế toàn bộ message chi tiết.\n\n**Phù hợp khi:** Hội thoại dài nhưng có thông tin quan trọng rải rác cần giữ lại (vd: agent hỗ trợ khách hàng qua nhiều lượt).\nKết hợp trigger theo độ dài, không chạy mỗi lượt\nSummarization tốn 1 lời gọi LLM - chỉ nên chạy khi `len(messages)` vượt ngưỡng (vd: \\> 20 message), không chạy sau mỗi lượt hội thoại.\n### Vector Memory\nLưu toàn bộ lịch sử vào vector store, chỉ **retrieve** phần liên quan đến câu hỏi hiện tại - giống RAG nhưng áp dụng cho memory thay vì tài liệu.",
              "codeLang": "python",
              "code": "def trim_messages(messages: list, max_messages: int = 20) -> list:\n    if len(messages) <= max_messages:\n        return messages\n    # Luôn giữ system message (nếu có) + N message gần nhất\n    system_msgs = [m for m in messages if m.get(\"role\") == \"system\"]\n    recent = messages[-max_messages:]\n    return system_msgs + recent",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-2-l3-t4",
              "title": "3. Context Compression",
              "lead": "Ngoài quản lý lịch sử hội thoại, cần nén cả kết quả tool call - đây thường là nguồn \"phình\" context lớn nhất (vd: search trả về 5000 từ nhưng chỉ 2 câu liên quan).",
              "concept": "Ngoài quản lý lịch sử hội thoại, cần nén cả **kết quả tool call** - đây thường là nguồn \"phình\" context lớn nhất (vd: search trả về 5000 từ nhưng chỉ 2 câu liên quan).\n### Nén tool output\n\nĐừng nén quá sớm\nNén mất thông tin không thể phục hồi. Chỉ nén khi thực sự cần (gần chạm giới hạn context) hoặc khi biết chắc phần bị cắt không quan trọng cho task hiện tại. Nén quá tay là nguyên nhân phổ biến khiến agent \"quên\" chi tiết quan trọng.",
              "codeLang": "python",
              "code": "def compress_tool_result(raw_result: str, query: str, max_tokens: int = 300) -> str:\n    \"\"\"Tóm tắt kết quả tool trước khi đưa vào context, giữ phần liên quan đến query.\"\"\"\n    if len(raw_result) < max_tokens * 4:  # Ước lượng thô: 1 token ≈ 4 ký tự\n        return raw_result\n\n    compress_prompt = f\"\"\"Trích xuất thông tin liên quan đến câu hỏi từ kết quả sau.\nGiữ số liệu, tên riêng chính xác. Bỏ phần không liên quan.\n\nCâu hỏi: {query}\nKết quả thô: {raw_result[:4000]}\n\nThông tin liên quan (ngắn gọn):\"\"\"\n\n    return llm.invoke(compress_prompt).content",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-2-l3-t5",
              "title": "4. Context Rot",
              "lead": "Đây là \"kẻ giết agent thầm lặng\". Compaction (mục 2-3) giải quyết bài toán context tràn (vượt giới hạn window). Nhưng có một vấn đề tinh vi hơn: chất lượng output suy giảm ngay cả khi window chưa đầy.",
              "concept": "Đây là \"kẻ giết agent thầm lặng\". Compaction (mục 2-3) giải quyết bài toán **context tràn** (vượt giới hạn window). Nhưng có một vấn đề tinh vi hơn: chất lượng output **suy giảm ngay cả khi window chưa đầy**.\n### Context Rot vs Context Overflow\n|  | Context Overflow | Context Rot |\n| --- | --- | --- |\n| **Là gì** | Context vượt giới hạn window | Chất lượng giảm dù còn trong giới hạn |\n| **Khi nào** | Ở 100% dung lượng | Bắt đầu từ \\~25-40% dung lượng |\n| **Biểu hiện** | Lỗi / crash | Suy giảm chất lượng khó nhận ra |\n| **Nhìn thấy?** | Ngay lập tức | Thường vô hình đến khi gây lỗi nghiêm trọng |\n| **Cách xử lý** | Compaction (cắt/tóm tắt) | Context engineering (cấu trúc) |\nModel có window 200K token vẫn có thể suy giảm ở 50K\nNghiên cứu của Chroma (2025) test 18 model frontier (GPT-4.1, Claude Opus 4, Gemini 2.5...) và phát hiện **mọi model** đều bị context rot ở mọi mức độ dài input được test. Window cho biết \\*bao nhiêu token vừa\\*, không cho biết \\*model dùng hiệu quả được bao nhiêu\\*.\n### Ba cơ chế gây rot\n| Cơ chế | Mô tả |\n| --- | --- |\n| **Lost-in-the-middle** | Model chú ý tốt phần **đầu và cuối** context, kém phần **giữa**. Thông tin quan trọng nằm giữa hội thoại dài gần như vô hình. |\n| **Attention dilution** | Attention là bậc hai: càng nhiều token, \"spotlight\" của model càng loãng. Ở 5K token là chùm sáng tập trung; ở 100K là ánh sáng tản ra 20x diện tích. |\n| **Distractor interference** | Nội dung tương tự về mặt ngữ nghĩa nhưng **không liên quan** chủ động đánh lạc hướng reasoning. Nhiễu \"giống signal\" tệ hơn nhiễu ngẫu nhiên. |\nBa cơ chế này **cộng hưởng nhân lên**, nên context rot là **siêu tuyến tính**: gấp đôi context gây suy giảm nhiều hơn gấp đôi.\n### Instruction Fade-Out & Agent Drift\nKhi hội thoại dài ra, model dần **quên system prompt ban đầu** - các log thực thi đẩy system prompt ra ngoài rìa vùng chú ý hiệu quả. Hệ quả là **agent drift** với 3 dạng:\n- **Goal drift**: agent dần đi lệch mục tiêu gốc (từ \"fix bug login\" → refactor auth → redesign toàn bộ kiến trúc).\n- **Reasoning drift**: chuỗi suy luận kém mạch lạc dần, xây trên kết luận sai ở bước trước.\n- **Context drift**: các lần gọi tool lỗi, traceback dài, reasoning đã lỗi thời chồng chất, lấn át signal.\n### Nguyên tắc 40-60%\nĐóng góp thực tiễn nhất từ HumanLayer: **giữ mức sử dụng context trong khoảng 40-60%** mọi lúc.\n\nĐiều này **quyết liệt hơn** chuẩn ngành (đa số agent nén ở 80-95%), nhưng giảm đáng kể context rot.\n### Các cách phòng thủ chính\n| Phòng thủ | Cách làm |\n| --- | --- |\n| **Compact sớm & chủ động** | Áp dụng nguyên tắc 40-60%, đừng đợi window đầy |\n| **Re-inject instructions** | Chèn lại chỉ dẫn quan trọng ở **cuối** context (vị trí attention cao), không chỉ dựa vào system prompt ở đầu - đây là cách hiệu quả nhất chống instruction fade-out |\n| **Sub-agent cho việc \"nhiễu\"** | Giao search/exploration cho sub-agent có context sạch riêng; agent chính chỉ nhận kết quả tinh gọn (Anthropic: cải thiện 90.2% nhờ context isolation) |\n| **Strip nội dung phục hồi được** | Nội dung file có thể đọc lại từ disk → thay bằng ghi chú \"\\[đã đọc file X, đọc lại nếu cần\\]\" thay vì giữ toàn bộ |\n| **Structured sections** | Đặt thông tin vào các mục có header rõ ràng (## MỤC TIÊU, ## QUYẾT ĐỊNH, ## KHÔNG LÀM) để model dễ chú ý |\n| **Task anchoring** | Chèn định kỳ mục tiêu gốc + phạm vi (in/out of scope) để chống goal drift |\nRe-inject ở cuối context: cách hiệu quả nhất\nLost-in-the-middle nghĩa là chỉ dẫn ở đầu system prompt mất dần ảnh hưởng khi hội thoại dài. Đặt lại chỉ dẫn quan trọng ở **cuối** context (vị trí gần nhất = attention cao nhất) là cách rẻ và hiệu quả nhất để agent không \"quên\" quy tắc. Đây chính là lý do Claude Code re-inject [CLAUDE.md](http://CLAUDE.md) sau mỗi lần compaction.\nContext Engineering là bước tiến hoá của Prompt Engineering\nPrompt engineering (Module I) tập trung vào **nội dung system prompt**. Context engineering tập trung vào **toàn bộ token trong window** (system + messages + tools + memory) và **duy trì chất lượng theo thời gian**, không chỉ ở lần gọi đầu. Với agent chạy dài, đây mới là kỹ năng quyết định.",
              "codeLang": "python",
              "code": "# Compact chủ động, không đợi đến khi gần đầy\nif context_usage > 0.40:\n    consider_compaction()   # Cân nhắc nén\nif context_usage > 0.60:\n    definitely_compact()    # Chắc chắn nén\nif context_usage > 0.85:\n    emergency_compact()     # Nén khẩn cấp",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-2-l3-t6",
              "title": "5. Hands-on: Multi-turn Agent + Vector Memory",
              "lead": "Dùng lại hàm formatmessages đã định nghĩa ở phần Summarization.",
              "concept": "Dùng lại hàm `format_messages` đã định nghĩa ở phần Summarization.",
              "codeLang": "python",
              "code": "from typing import TypedDict, Annotated\nfrom langgraph.graph import StateGraph, START, END\nfrom langgraph.graph.message import add_messages\nfrom langgraph.checkpoint.memory import MemorySaver\nfrom langchain_openai import ChatOpenAI, OpenAIEmbeddings\nfrom langchain_community.vectorstores import Chroma\n\n# ====== LONG-TERM MEMORY STORE ======\nembedding = OpenAIEmbeddings(model=\"text-embedding-3-small\")\nlong_term_memory = Chroma(collection_name=\"user_memory\", embedding_function=embedding)\n\ndef save_to_long_term(user_id: str, fact: str):\n    long_term_memory.add_texts([fact], metadatas=[{\"user_id\": user_id}])\n\ndef recall_long_term(user_id: str, query: str, k: int = 3) -> list[str]:\n    results = long_term_memory.similarity_search(query, k=k, filter={\"user_id\": user_id})\n    return [d.page_content for d in results]\n\n# ====== STATE ======\nclass AgentState(TypedDict):\n    messages: Annotated[list, add_messages]\n    user_id: str\n\nllm = ChatOpenAI(model=\"gpt-4o-mini\", temperature=0.3)\n\n# ====== NODES ======\ndef recall_node(state: AgentState) -> dict:\n    \"\"\"Truy xuất long-term memory liên quan trước khi trả lời.\"\"\"\n    last_user_msg = state[\"messages\"][-1].content\n    memories = recall_long_term(state[\"user_id\"], last_user_msg)\n    if memories:\n        context = \"Thông tin đã biết về user:\\n\" + \"\\n\".join(f\"- {m}\" for m in memories)\n        return {\"messages\": [{\"role\": \"system\", \"content\": context}]}\n    return {}\n\ndef agent_node(state: AgentState) -> dict:\n    # Sliding window: chỉ gi",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-2-l3-t7",
              "title": "Tóm tắt",
              "lead": "mermaid",
              "concept": "| Khái niệm | Ghi nhớ |\n| --- | --- |\n| Short-term | Context của session hiện tại, sống trong graph state |\n| Long-term | Xuyên session, cần external store (DB/vector store) |\n| Episodic | \"Chuyện gì đã xảy ra\" - gắn thời điểm |\n| Semantic | \"Sự thật là gì\" - không gắn thời điểm |\n| Procedural | \"Cách làm task X\" - system prompt / learned rules |\n| Sliding window | Rẻ, mất thông tin hoàn toàn |\n| Summarization | Vừa phải, nén nhưng giữ ý chính |\n| Vector memory | Tốt cho long-term, cần retrieve đúng |\n| Context compression | Áp dụng cho tool output, không chỉ hội thoại |\n| Context Rot | Chất lượng giảm dù chưa tràn window - bắt đầu từ \\~25-40% |\n| Nguyên tắc 40-60% | Compact chủ động, đừng đợi đến khi gần đầy |\n| Re-injection | Chèn lại chỉ dẫn quan trọng ở cuối context, chống fade-out |",
              "codeLang": "mermaid",
              "code": "graph TD\n    Q{Thông tin cần nhớ?} --> A[Chỉ trong task/session hiện tại]\n    Q --> B[Xuyên suốt nhiều session]\n    A --> ST[Short-term: state.messages]\n    B --> C{Loại thông tin?}\n    C --> EP[Sự kiện cụ thể] --> EPS[Episodic memory]\n    C --> SEM[Sự thật chung] --> SEMS[Semantic memory - Vector store]\n    C --> PROC[Quy trình xử lý] --> PROCS[Procedural - System prompt]\n\n    ST --> SIZE{Context quá dài?}\n    SIZE -->|Có, casual| SW[Sliding window]\n    SIZE -->|Có, cần giữ ý chính| SUM[Summarization]\n    SIZE -->|Đã tràn?| ROT{Chưa tràn nhưng<br/>output kém đi?}\n    ROT -->|Có| RULE[Context Rot -<br/>áp dụng nguyên tắc 40-60%]",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            }
          ]
        },
        {
          "id": "module-2-l4",
          "title": "Bài 4: Agentic Tool Design & Integration",
          "badge": "6 mục",
          "topics": [
            {
              "id": "module-2-l4-t1",
              "title": "Tổng quan",
              "lead": "Chất lượng agent phụ thuộc rất nhiều vào chất lượng tool - tool thiết kế tồi khiến model gọi sai, gọi thừa, hoặc không biết khi nào dùng. Bài này bao gồm nguyên tắc thiết kế tool, chiến lược chọn tool khi có hàng trăm tool (bao gồm khủng ho",
              "concept": "Chất lượng agent phụ thuộc rất nhiều vào chất lượng tool - tool thiết kế tồi khiến model gọi sai, gọi thừa, hoặc không biết khi nào dùng. Bài này bao gồm nguyên tắc thiết kế tool, chiến lược chọn tool khi có hàng trăm tool (bao gồm khủng hoảng tool sprawl và cách phòng thủ bằng progressive disclosure), bảo mật khi thực thi tool do LLM quyết định, và chuẩn MCP để chuẩn hoá tích hợp.",
              "codeLang": "text",
              "code": "",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-2-l4-t2",
              "title": "1. Tool Design Principles",
              "lead": "Atomic tool làm đúng 1 việc. Composite tool gộp nhiều bước thành 1 lời gọi.",
              "concept": "|  | Atomic | Composite |\n| --- | --- | --- |\n| Số lời gọi LLM | Nhiều hơn (model tự nối các bước) | Ít hơn (1 lời gọi = nhiều thao tác) |\n| Linh hoạt | Cao - model tự quyết định thứ tự, có thể bỏ bước không cần | Thấp - luôn chạy full quy trình dù chỉ cần 1 phần |\n| Độ trễ | Cao hơn (nhiều round-trip với LLM) | Thấp hơn (gộp trong 1 lần thực thi) |\n| Dễ debug | Dễ hơn - mỗi tool 1 trách nhiệm rõ ràng | Khó hơn - lỗi có thể ở bất kỳ bước con nào |\n**Nguyên tắc chọn**\nBắt đầu với atomic tools. Chỉ gộp thành composite khi đo được rằng model **luôn** gọi một chuỗi tool cố định theo cùng thứ tự - lúc đó composite giảm latency mà không mất linh hoạt thực tế.\n### Error Handling\nTool phải trả về lỗi dưới dạng model **đọc hiểu được**, không phải raise exception làm crash agent.\n\n**Không để exception văng lên tận agent loop**\nNếu tool raise exception không bắt, toàn bộ graph crash thay vì cho model cơ hội thử cách khác. Luôn bọc logic tool trong try/except và trả về **message lỗi rõ ràng** để model tự quyết định bước tiếp theo (thử lại, hỏi user, dùng tool khác).\n### Idempotency\nVới tool có side effect (gửi email, tạo đơn hàng, xoá dữ liệu), cần đảm bảo gọi nhiều lần không gây hậu quả nhân đôi - vì model có thể gọi lại tool do retry hoặc do reasoning lặp.\n\n**Áp dụng cho:** Mọi tool có side effect không thể hoàn tác dễ dàng - đặt hàng, gửi email/SMS, thanh toán, xoá dữ liệu.",
              "codeLang": "python",
              "code": "# Atomic - 3 tool riêng biệt\n@tool\ndef get_customer(customer_id: str) -> dict:\n    \"\"\"Lấy thông tin khách hàng theo ID.\"\"\"\n    ...\n\n@tool\ndef get_orders(customer_id: str) -> list:\n    \"\"\"Lấy danh sách đơn hàng của khách hàng.\"\"\"\n    ...\n\n@tool\ndef get_payment_status(order_id: str) -> str:\n    \"\"\"Lấy trạng thái thanh toán của đơn hàng.\"\"\"\n    ...",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-2-l4-t3",
              "title": "2. Tool Selection",
              "lead": "Khi agent có hàng chục đến hàng trăm tool, nhét toàn bộ schema vào mỗi lời gọi LLM vừa tốn token vừa khiến model dễ chọn nhầm tool.",
              "concept": "Khi agent có hàng chục đến hàng trăm tool, nhét toàn bộ schema vào mỗi lời gọi LLM vừa tốn token vừa khiến model dễ chọn nhầm tool.\n### Khủng hoảng Tool Sprawl\nKết nối agent với nhiều MCP server (Bài 1, Bài 4 mục 4) rất dễ - và đó chính là vấn đề. Việc dễ kết nối khiến người ta kết nối quá nhiều tool mà không chọn lọc, và hệ quả đo được rất rõ:\n| Chỉ số | Số liệu thực tế |\n| --- | --- |\n| Context bị tool chiếm (3 MCP server) | **143K/200K token (72%)** trước khi đọc tin nhắn user |\n| GitHub MCP server mặc định | **91 tool definitions** |\n| Độ chính xác chọn tool (bộ tool gọn) | \\~43% |\n| Độ chính xác chọn tool (bộ tool phình to) | Dưới 14% (giảm 3 lần) |\n| Ngưỡng chính xác thực tế | **5-7 tool** cho độ chính xác ổn định |\n**Nhiều tool hơn không có nghĩa là agent giỏi hơn**\nVới \\> 20 tool, model dễ nhầm giữa các tool tên/mô tả tương tự (`github_create_issue` vs `github_create_pull_request` vs `github_create_release`...) và bắt đầu **hallucinate tham số**. Đây là nguyên nhân phổ biến khiến agent \"thông minh\" hoạt động tệ hơn khi được cấp thêm quyền truy cập tool.\n### Hierarchical Grouping\nChia tool thành nhóm theo domain, chỉ nạp nhóm liên quan dựa trên intent của user.\n\n| Chiến lược | Phù hợp khi | Đánh đổi |\n| --- | --- | --- |\n| Nạp toàn bộ tool | \\< 10-15 tool | Đơn giản, nhưng không scale |\n| Hierarchical grouping | Tool có domain rõ ràng, số nhóm cố định | Cần bước classify trước, có thể phân loại sai |\n| Tool retrieval (embedding) | Hàng trăm tool, domain đa dạng | Thêm độ trễ + chi phí embedding, có thể miss tool đúng nếu description mơ hồ |\n**Chất lượng description quyết định retrieval**\nTool retrieval chỉ tốt bằng chất lượng `description` của tool. Viết description theo văn phong người dùng sẽ hỏi (\"tìm nhà hàng theo khu vực\"), không theo văn phong kỹ thuật (\"query restaurant table by location_id\").\n### Tool Search: Meta-tool thay vì nạp toàn bộ\nThay vì nạp tất cả schema vào mỗi request, cấp cho agent **một tool duy nhất** để tự tìm tool khi cần - cách tiếp cận mà Anthropic dùng trong Claude Code.\n\nAgent bắt đầu chỉ với `tool_search`, tự tìm và \"khám phá\" tool phù hợp, rồi mới gọi. Dữ liệu của Anthropic: giảm **85% token** so với nạp toàn bộ. Đánh đổi là thêm 1 vòng round-trip LLM - nhưng vì mỗi lời gọi có context nhỏ hơn nhiều, tổng thời gian thường vẫn **nhanh hơn** do model xử lý input ngắn nhanh hơn đáng kể.\n### Progressive Disclosure 3 tầng (cho Skills)\nKhi agent có nhiều **skill** (quy trình nhiều bước, không chỉ 1 tool đơn lẻ - xem MCP ở mục 4), áp dụng nguyên tắc: nạp **metadata trước, hướng dẫn chi tiết sau, tài nguyên phụ trợ cuối cùng**.\n| Tầng | Nội dung | Khi nào nạp | Kích thước |\n| --- | --- | --- | --- |\n| **Tầng 1 - Discovery** | Tên + mô tả ngắn của mọi skill | Luôn có trong context | \\~100 token/skill |\n| **Tầng 2 - Activation** | Hướng dẫn đầy đủ (các bước, error handling) | Khi agent quyết định dùng skill đó | \\~500-2000 token |\n| **Tầng 3 - Execution** | File tham chiếu, script hỗ trợ | Khi một bước cụ thể cần đến | Theo nhu cầu |",
              "codeLang": "python",
              "code": "TOOL_GROUPS = {\n    \"calendar\": [check_calendar, create_event, cancel_event],\n    \"finance\": [get_stock_price, get_exchange_rate, calculate_tax],\n    \"customer_support\": [get_customer, get_orders, create_ticket],\n}\n\ndef classify_intent(user_message: str) -> str:\n    \"\"\"Phân loại nhanh xem câu hỏi thuộc nhóm nào.\"\"\"\n    classify_prompt = f\"\"\"Câu hỏi sau thuộc nhóm nào: calendar, finance, customer_support?\nChỉ trả về 1 từ.\n\nCâu hỏi: {user_message}\"\"\"\n    return llm.invoke(classify_prompt).content.strip().lower()\n\ndef get_relevant_tools(user_message: str) -> list:\n    group = classify_intent(user_message)\n    return TOOL_GROUPS.get(group, [])",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-2-l4-t4",
              "title": "3. Tool Security",
              "lead": "Tool cho phép LLM hành động trong thế giới thực - đây là bề mặt tấn công lớn nhất của agent (prompt injection từ tài liệu/web có thể khiến model gọi tool ngoài ý muốn user).",
              "concept": "Tool cho phép LLM **hành động** trong thế giới thực - đây là bề mặt tấn công lớn nhất của agent (prompt injection từ tài liệu/web có thể khiến model gọi tool ngoài ý muốn user).\n### Sandboxing\nTool thực thi code hoặc truy cập filesystem/network phải chạy trong môi trường cô lập.\n\n**Không bao giờ chạy code do LLM sinh ra trực tiếp trên host**\n`exec()` hay `subprocess` trực tiếp trên máy chủ ứng dụng là lỗ hổng nghiêm trọng - prompt injection có thể khiến model sinh code độc hại. Luôn dùng container cô lập (`--network=none`, giới hạn memory/CPU, không mount volume nhạy cảm).\n### Rate Limiting\nGiới hạn số lần agent được gọi tool (đặc biệt tool tốn phí hoặc có side effect) trong 1 khoảng thời gian/session.\n\n**Audit log khác observability (Bài 5)**\nAudit log tập trung vào **trách nhiệm giải trình** (ai làm gì, khi nào, để điều tra sau) - thường là log bất biến, giữ lâu dài vì lý do compliance. Observability (Bài 5) tập trung vào **hiệu năng và chất lượng** (latency, cost, trajectory) - để cải thiện hệ thống. Hai mục đích khác nhau dù dữ liệu có thể overlap.",
              "codeLang": "python",
              "code": "import subprocess\n\n@tool\ndef run_python_code(code: str) -> str:\n    \"\"\"Chạy code Python trong sandbox, trả về output. Không có quyền truy cập network/filesystem ngoài thư mục tạm.\"\"\"\n    try:\n        result = subprocess.run(\n            [\"docker\", \"run\", \"--rm\", \"--network=none\",\n             \"--memory=256m\", \"--cpus=0.5\",\n             \"python-sandbox:latest\", \"python\", \"-c\", code],\n            capture_output=True, text=True, timeout=10,\n        )\n        return result.stdout or result.stderr\n    except subprocess.TimeoutExpired:\n        return \"Lỗi: Code chạy quá 10 giây, đã bị dừng.\"",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-2-l4-t5",
              "title": "4. MCP: Standards, Server, Clients",
              "lead": "MCP (Model Context Protocol) chuẩn hoá cách agent giao tiếp với tool/data source, đã giới thiệu khái niệm ở Bài 1. Phần này đi vào cách implement.",
              "concept": "MCP (Model Context Protocol) chuẩn hoá cách agent giao tiếp với tool/data source, đã giới thiệu khái niệm ở Bài 1. Phần này đi vào cách implement.\n### Kiến trúc\n\nMCP giao tiếp qua **JSON-RPC**, mỗi Server expose 3 loại primitive:\n| Primitive | Vai trò | Tương đương |\n| --- | --- | --- |\n| **Tools** | Hành động Server cho phép Client gọi | Function calling |\n| **Resources** | Dữ liệu Server expose để đọc | Tài liệu / file |\n| **Prompts** | Template prompt tái sử dụng được Server cung cấp | Prompt library |\n### Viết một MCP Server tối giản\n\n**MCP giá trị nhất khi tool được tái sử dụng ở nhiều agent/app**\nNếu chỉ có 1 agent dùng 1 tool nội bộ, viết `@tool` trực tiếp (như Bài 2) đơn giản hơn. MCP đáng giá khi cùng 1 tool/data source cần phục vụ nhiều agent khác nhau (vd: news scraper dùng cho cả research agent lẫn chatbot khác) - viết 1 Server, mọi Client đều dùng lại được.",
              "codeLang": "mermaid",
              "code": "graph LR\n    subgraph \"MCP Host (Agent App)\"\n        AGENT[Agent / LangGraph]\n        CLIENT[MCP Client]\n    end\n    subgraph \"MCP Servers\"\n        S1[Filesystem Server]\n        S2[Vietnamese News Server]\n        S3[Database Server]\n    end\n    AGENT --> CLIENT\n    CLIENT -->|JSON-RPC| S1\n    CLIENT -->|JSON-RPC| S2\n    CLIENT -->|JSON-RPC| S3",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-2-l4-t6",
              "title": "Tóm tắt",
              "lead": "mermaid",
              "concept": "| Nguyên tắc | Ghi nhớ |\n| --- | --- |\n| Atomic vs Composite | Bắt đầu atomic, gộp composite khi đo được pattern cố định |\n| Error handling | Trả lỗi dạng text model đọc được, không raise exception |\n| Idempotency | Bắt buộc cho tool có side effect không hoàn tác được |\n| Hierarchical grouping | Nhóm tool theo domain, classify intent trước khi nạp |\n| Tool retrieval | Embedding similarity khi có hàng trăm tool |\n| Tool sprawl | \\> 20 tool: độ chính xác chọn tool giảm mạnh, dễ hallucinate tham số |\n| Tool search | Meta-tool duy nhất để agent tự khám phá tool khi cần, giảm \\~85% token |\n| Progressive disclosure | Nạp metadata trước, hướng dẫn chi tiết sau, tài nguyên cuối cùng |\n| Nguyên tắc 5-Tool | Giới hạn cứng mỗi agent tối đa 5 tool - chuyên gia hẹp thay vì biết tuốt |\n| Sandboxing | Không bao giờ exec code LLM sinh ra trực tiếp trên host |\n| Rate limiting | Giới hạn theo session + tool, đặc biệt tool tốn phí |\n| Audit logs | Bắt buộc cho side-effect tools, phục vụ compliance |\n| MCP | Chuẩn hoá khi 1 tool cần phục vụ nhiều agent/app |",
              "codeLang": "mermaid",
              "code": "graph TD\n    A[Thiết kế tool mới] --> B{Model có luôn gọi<br/>chuỗi cố định không?}\n    B -->|Không| ATOMIC[Atomic tools]\n    B -->|Có| COMP[Composite tool]\n    ATOMIC --> ERR[Bọc try/except,<br/>trả lỗi dạng đọc được]\n    COMP --> ERR\n    ERR --> SIDE{Có side effect?}\n    SIDE -->|Có| IDEM[Thêm idempotency key<br/>+ audit log]\n    SIDE -->|Không| DONE[Sẵn sàng]\n    IDEM --> SEC{Thực thi code/<br/>truy cập hệ thống?}\n    SEC -->|Có| SANDBOX[Sandbox + rate limit]\n    SEC -->|Không| DONE",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            }
          ]
        },
        {
          "id": "module-2-l5",
          "title": "Bài 5: Agent Evaluation & Observability",
          "badge": "5 mục",
          "topics": [
            {
              "id": "module-2-l5-t1",
              "title": "Tổng quan",
              "lead": "RAGAS và LLM-as-judge (Module I, Bài 7) đánh giá output cuối cùng - đủ cho RAG nhưng không đủ cho agent, vì agent có thể ra đúng đáp án bằng con đường sai (hoặc tốn kém, hoặc nguy hiểm). Bài này mở rộng evaluation sang trajectory - toàn bộ ",
              "concept": "RAGAS và LLM-as-judge (Module I, Bài 7) đánh giá output cuối cùng - đủ cho RAG nhưng không đủ cho agent, vì agent có thể ra đúng đáp án bằng con đường sai (hoặc tốn kém, hoặc nguy hiểm). Bài này mở rộng evaluation sang **trajectory** - toàn bộ chuỗi hành động agent thực hiện - và cách giám sát agent trong production.",
              "codeLang": "text",
              "code": "",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-2-l5-t2",
              "title": "1. Eval Dimensions",
              "lead": "mermaid",
              "concept": "| Chiều đánh giá | Câu hỏi | Ví dụ vấn đề nếu bỏ qua |\n| --- | --- | --- |\n| **Task Success** | Agent có hoàn thành mục tiêu người dùng đề ra không? | Đây là metric \"must-have\" nhưng không đủ - có thể đúng do may mắn |\n| **Trajectory Quality** | Chuỗi bước có logic, không lặp vô ích, không đi đường vòng? | Agent trả lời đúng nhưng gọi tool 15 lần cho task cần 3 lần |\n| **Tool Accuracy** | Có chọn đúng tool? Tham số truyền vào có chính xác? | Agent gọi `get_weather(city=\"Hà Lội\")`  • lỗi chính tả khiến tool fail |\n| **Cost & Latency** | Tổng token, tổng thời gian, tổng số lời gọi LLM/tool? | 2 agent cùng ra đúng đáp án nhưng 1 agent tốn gấp 5 lần chi phí |\nTask Success cao không có nghĩa là agent tốt. Một agent có thể đạt task success 95% nhưng trajectory kém - gọi tool thừa, lãng phí chi phí, hoặc thực hiện hành động rủi ro (xoá nhầm dữ liệu rồi tạo lại) mà vẫn ra kết quả đúng cuối cùng. Production cần đánh giá cả 4 chiều, không chỉ chiều cuối.",
              "codeLang": "mermaid",
              "code": "graph TD\n    EVAL[Agent Evaluation] --> TS[Task Success<br/>Có đạt mục tiêu không?]\n    EVAL --> TQ[Trajectory Quality<br/>Con đường đi có hợp lý không?]\n    EVAL --> TA[Tool Accuracy<br/>Chọn đúng tool, đúng tham số?]\n    EVAL --> CL[Cost & Latency<br/>Có hiệu quả không?]",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-2-l5-t3",
              "title": "2. Methodologies",
              "lead": "So sánh output cuối với expected outcome - tương tự LLM-as-judge ở Module I nhưng áp dụng cho toàn bộ agent run.",
              "concept": "**Phù hợp khi:** Test case có đáp án đúng/sai rõ ràng (tool nào nên/không nên được gọi, giới hạn retry có được tôn trọng không) - nhanh, rẻ, chạy được trong CI.\n### So sánh methodologies\n| Phương pháp | Chi phí | Tốc độ | Phát hiện được |\n| --- | --- | --- | --- |\n| Unit tests | Thấp | Nhanh (không cần LLM) | Lỗi rõ ràng, có thể assert được |\n| End-to-end (LLM judge) | Trung bình | Trung bình | Task có hoàn thành không |\n| Trajectory eval | Cao (chuỗi dài) | Chậm | Hiệu quả, đường đi hợp lý, tool đúng |",
              "codeLang": "python",
              "code": "from openai import OpenAI\nimport json\n\nclient = OpenAI()\n\ndef evaluate_task_success(task: str, final_output: str, success_criteria: str) -> dict:\n    judge_prompt = f\"\"\"Đánh giá agent có hoàn thành nhiệm vụ không.\n\nNhiệm vụ: {task}\nTiêu chí thành công: {success_criteria}\nKết quả agent trả về: {final_output}\n\nTrả về JSON: {{\"success\": true/false, \"score\": 0-1, \"reasoning\": \"...\"}}\"\"\"\n\n    response = client.chat.completions.create(\n        model=\"gpt-4o-mini\",\n        messages=[{\"role\": \"user\", \"content\": judge_prompt}],\n        response_format={\"type\": \"json_object\"},\n    )\n    return json.loads(response.choices[0].message.content)",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-2-l5-t4",
              "title": "3. Observability",
              "lead": "Evaluation chạy offline (trước khi deploy, trên test set). Observability giám sát agent online (production, real-time).",
              "concept": "Evaluation chạy **offline** (trước khi deploy, trên test set). Observability giám sát agent **online** (production, real-time).\n### Tracing với LangSmith\n\nTrace của agent hiển thị dạng cây, phản ánh đúng graph: node nào gọi node nào, tool nào được gọi với tham số gì, mất bao lâu, tốn bao nhiêu token - khác với trace của 1 lời gọi LLM đơn (Module I) vốn chỉ là 1 span phẳng.\n### LangFuse (self-hosted alternative)\n\n| Công cụ | Điểm mạnh | Dùng khi |\n| --- | --- | --- |\n| **LangSmith** | Tích hợp sâu với LangGraph/LangChain, dashboard sẵn cho agent trace | Stack chính là LangChain/LangGraph |\n| **LangFuse** | Open-source, tự host được, không vendor lock-in | Cần kiểm soát dữ liệu, ngân sách hạn chế |\n| **OpenTelemetry** | Chuẩn mở, tích hợp được với hệ thống ngoài LLM (backend, DB) | Kiến trúc đa framework, cần trace xuyên suốt toàn hệ thống |\n### Metrics cần giám sát cho Agent (mở rộng từ Module I)\n| Metric | Mô tả | Alert threshold |\n| --- | --- | --- |\n| Task success rate | % task hoàn thành đúng | \\< 90% |\n| Avg steps per task | Số bước trung bình để hoàn thành | Tăng đột biến so với baseline |\n| Tool error rate | % tool call thất bại | \\> 5% |\n| Cost per task | Tổng token × giá, trung bình mỗi task | Vượt budget |\n| Human intervention rate | % task cần HITL can thiệp | Tăng bất thường (dấu hiệu agent kém tự tin) |\n| Loop detection | Số lần agent lặp lại cùng 1 tool call | \\> 3 lần liên tiếp |",
              "codeLang": "python",
              "code": "import os\n\nos.environ[\"LANGCHAIN_TRACING_V2\"] = \"true\"\nos.environ[\"LANGCHAIN_API_KEY\"] = \"ls__...\"\nos.environ[\"LANGCHAIN_PROJECT\"] = \"vietnamese-research-agent\"\n\n# Mọi lời gọi LangGraph agent tự động được trace - mỗi node, mỗi tool call,\n# mỗi token usage đều xuất hiện trên dashboard LangSmith\nresult = app.invoke({\"messages\": [...]}, config=config)",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-2-l5-t5",
              "title": "Tóm tắt",
              "lead": "mermaid",
              "concept": "| Khái niệm | Ghi nhớ |\n| --- | --- |\n| Task Success | Cần nhưng không đủ - đúng đáp án không đồng nghĩa quá trình tốt |\n| Trajectory Quality | Đánh giá cả con đường đi, không chỉ đích đến |\n| Tool Accuracy | Chọn đúng tool + đúng tham số |\n| Cost & Latency | So sánh hiệu quả giữa các agent cùng đạt task success |\n| Unit tests | Nhanh, rẻ, cho case có đáp án xác định - chạy trong CI |\n| Trajectory eval | Cần LLM judge, phát hiện lãng phí/đi đường vòng |\n| LangSmith/LangFuse | Trace cây phản ánh cấu trúc graph, khác trace phẳng của Module I |\n| Loop detection | Metric đặc thù agent - phát hiện agent kẹt lặp vô ích |",
              "codeLang": "mermaid",
              "code": "graph TD\n    A[Đánh giá agent] --> B{Offline hay Online?}\n    B -->|Offline, trước deploy| C[Evaluation]\n    B -->|Online, production| D[Observability]\n    C --> E{Loại kiểm tra?}\n    E -->|Đáp án rõ ràng| F[Unit tests]\n    E -->|Đánh giá output| G[End-to-end LLM judge]\n    E -->|Đánh giá quá trình| H[Trajectory eval]\n    D --> I[LangSmith / LangFuse / OpenTelemetry]\n    I --> J[Giám sát: success rate, cost, tool errors, loop detection]",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            }
          ]
        },
        {
          "id": "module-2-l6",
          "title": "Bài 6: Multi-Agent Systems",
          "badge": "5 mục",
          "topics": [
            {
              "id": "module-2-l6-t1",
              "title": "Tổng quan",
              "lead": "Một agent với quá nhiều tool và trách nhiệm trở nên khó kiểm soát - system prompt phình to, model dễ nhầm lẫn giữa các domain. Bài này trình bày các pattern chia nhỏ công việc cho nhiều agent chuyên biệt, so sánh framework hỗ trợ multi-agen",
              "concept": "Một agent với quá nhiều tool và trách nhiệm trở nên khó kiểm soát - system prompt phình to, model dễ nhầm lẫn giữa các domain. Bài này trình bày các pattern chia nhỏ công việc cho nhiều agent chuyên biệt, so sánh framework hỗ trợ multi-agent, và thực hành xây dựng hệ thống multi-agent với LangGraph - nền tảng trực tiếp cho capstone.",
              "codeLang": "text",
              "code": "",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-2-l6-t2",
              "title": "1. Patterns",
              "lead": "mermaid",
              "concept": "### Sequential\nAgent chạy theo thứ tự cố định, output của agent trước là input của agent sau.\n\n**Phù hợp khi:** Quy trình có thứ tự rõ ràng, không cần agent quay lại bước trước (vd: research → phân tích → viết báo cáo).\n### Hierarchical (Supervisor)\nMột **Supervisor agent** nhận task, quyết định giao cho Worker agent nào, tổng hợp kết quả - Worker không giao tiếp trực tiếp với nhau.\n\n**Phù hợp khi:** Task cần định tuyến động (không biết trước cần Worker nào), cần kiểm soát tập trung về thứ tự và điều phối.\n### Collaborative\nNhiều agent cùng thảo luận, phản biện lẫn nhau trước khi chốt kết quả - không có thứ bậc cố định.",
              "codeLang": "mermaid",
              "code": "graph TD\n    P[Multi-Agent Patterns] --> SEQ[Sequential<br/>Agent A → B → C]\n    P --> HIER[Hierarchical<br/>Supervisor điều phối Workers]\n    P --> COLLAB[Collaborative<br/>Nhiều agent cùng bàn bạc]\n    P --> SWARM[Swarm<br/>Agent tự chuyển giao ngang hàng]",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-2-l6-t3",
              "title": "2. Framework Comparison",
              "lead": "| Framework | Cách biểu diễn multi-agent | Điểm mạnh | Điểm yếu |",
              "concept": "| Framework | Cách biểu diễn multi-agent | Điểm mạnh | Điểm yếu |\n| --- | --- | --- | --- |\n| **LangGraph** | Mỗi agent là 1 subgraph/node, giao tiếp qua shared state | Kiểm soát chi tiết luồng dữ liệu, dễ debug, tích hợp checkpointer/HITL đã học | Cần tự code cấu trúc điều phối |\n| **CrewAI** | Định nghĩa \"Crew\" gồm nhiều \"Agent\" có role/goal, \"Task\" được gán cho agent | API cấp cao, khai báo nhanh (role, goal, backstory) | Ít linh hoạt khi cần logic điều phối phức tạp/rẽ nhánh |\n| **OpenAI Agents SDK** | \"Handoffs\" giữa các Agent, mỗi Agent có instructions + tools riêng | Đơn giản cho pattern Swarm, tích hợp chặt OpenAI models | Gắn với hệ sinh thái OpenAI, ít kiểm soát state chi tiết |\n| **AutoGen** | Agent giao tiếp qua conversation (message passing), có GroupChat | Mạnh cho Collaborative pattern, nhiều agent \"thảo luận\" | Khó kiểm soát chính xác luồng như graph tường minh |\n\nVì sao capstone vẫn dùng LangGraph cho multi-agent\nLangGraph biểu diễn multi-agent như **subgraph lồng trong graph lớn hơn** - state, checkpointer, HITL, và tool execution loop đã học ở Bài 2-4 dùng lại được nguyên vẹn cho từng agent con. Điều này tránh phải học lại 1 mental model mới hoàn toàn như khi chuyển sang CrewAI/AutoGen.",
              "codeLang": "python",
              "code": "# So sánh cú pháp: cùng 1 ý tưởng (Supervisor điều phối Researcher + Writer)\n\n# --- CrewAI ---\nresearcher = Agent(role=\"Researcher\", goal=\"Tìm thông tin chính xác\")\nwriter = Agent(role=\"Writer\", goal=\"Viết báo cáo dễ hiểu\")\ncrew = Crew(agents=[researcher, writer], tasks=[research_task, write_task], process=Process.sequential)\n\n# --- OpenAI Agents SDK ---\nresearcher = Agent(name=\"Researcher\", instructions=\"Tìm thông tin\", handoffs=[])\nwriter = Agent(name=\"Writer\", instructions=\"Viết báo cáo\", handoffs=[])\ntriage = Agent(name=\"Supervisor\", handoffs=[researcher, writer])",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-2-l6-t4",
              "title": "3. Hands-on: Multi-agent với LangGraph",
              "lead": "Ví dụ Supervisor điều phối 2 Worker: Researcher (tìm thông tin) và Writer (viết tóm tắt) - đơn giản hoá của kiến trúc capstone.",
              "concept": "Ví dụ Supervisor điều phối 2 Worker: Researcher (tìm thông tin) và Writer (viết tóm tắt) - đơn giản hoá của kiến trúc capstone.\n\nGiới hạn số vòng Supervisor ↔ Worker\nGiống ReAct loop (Bài 1-2), vòng lặp Supervisor → Worker → Supervisor có thể chạy vô hạn nếu Supervisor không bao giờ quyết định `done`. Luôn set `recursion_limit` và cân nhắc thêm đếm số vòng tối đa trong state.",
              "codeLang": "python",
              "code": "from typing import TypedDict, Annotated\nfrom langgraph.graph import StateGraph, START, END\nfrom langgraph.graph.message import add_messages\nfrom langchain_openai import ChatOpenAI\nfrom langchain_core.tools import tool\n\nllm = ChatOpenAI(model=\"gpt-4o-mini\", temperature=0.2)\n\n# ====== SHARED STATE ======\nclass SupervisorState(TypedDict):\n    messages: Annotated[list, add_messages]\n    task: str\n    research_notes: str\n    next_agent: str\n\n# ====== TOOLS cho Researcher ======\n@tool\ndef search_web(query: str) -> str:\n    \"\"\"Tìm kiếm thông tin trên web.\"\"\"\n    return f\"Kết quả tìm kiếm cho '{query}': [thông tin mô phỏng]\"\n\n# ====== SUPERVISOR NODE ======\nSUPERVISOR_PROMPT = \"\"\"Bạn điều phối 2 agent: 'researcher' (tìm thông tin) và 'writer' (viết báo cáo từ thông tin đã có).\nNhiệm vụ: {task}\nGhi chú nghiên cứu hiện có: {notes}\n\nQuyết định agent tiếp theo cần chạy. Nếu đã đủ thông tin để viết, chọn 'writer'.\nNếu đã có báo cáo hoàn chỉnh, chọn 'done'.\nChỉ trả về 1 từ: researcher, writer, hoặc done.\"\"\"\n\ndef supervisor_node(state: SupervisorState) -> dict:\n    decision = llm.invoke(SUPERVISOR_PROMPT.format(\n        task=state[\"task\"], notes=state.get(\"research_notes\", \"Chưa có\")\n    )).content.strip().lower()\n    return {\"next_agent\": decision}\n\ndef route_supervisor(state: SupervisorState) -> str:\n    return state[\"next_agent\"] if state[\"next_agent\"] in [\"researcher\", \"writer\"] else END\n\n# ====== RESEARCHER SUBGRAPH ======\ndef researcher_node(state: SupervisorState) -> dict:\n    llm_wi",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-2-l6-t5",
              "title": "Tóm tắt",
              "lead": "mermaid",
              "concept": "| Pattern | Ghi nhớ |\n| --- | --- |\n| Sequential | A → B → C cố định, không quay lại |\n| Hierarchical | Supervisor điều phối, Worker không giao tiếp trực tiếp |\n| Collaborative | Nhiều agent phản biện qua lại để tăng chất lượng |\n| Swarm | Handoff ngang hàng, phi tập trung |\n| LangGraph multi-agent | Subgraph + shared state, tái dùng checkpointer/HITL |\n| CrewAI | Nhanh cho prototype, khai báo role/goal cấp cao |\n| Giới hạn vòng lặp | Bắt buộc với mọi Supervisor loop, tránh chạy vô hạn |",
              "codeLang": "mermaid",
              "code": "graph TD\n    Q{Cấu trúc task?} --> A[Thứ tự cố định, biết trước các bước]\n    Q --> B[Cần định tuyến động giữa các domain worker]\n    Q --> C[Cần nhiều góc nhìn phản biện lẫn nhau]\n    Q --> D[Hội thoại chuyển domain linh hoạt, phi tập trung]\n    A --> SEQ[Sequential]\n    B --> HIER[Hierarchical - Supervisor]\n    C --> COLLAB[Collaborative]\n    D --> SWARM[Swarm]\n\n    HIER --> FW{Framework?}\n    FW --> LG[LangGraph - tái dùng state/HITL đã học]\n    FW --> CREW[CrewAI - khai báo nhanh role/goal]\n    FW --> OAI[OpenAI Agents SDK - handoffs đơn giản]",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            }
          ]
        },
        {
          "id": "module-2-l7",
          "title": "Bài 7: Capstone Project - Multi-Agent Vietnamese Research Assistant",
          "badge": "3 mục",
          "topics": [
            {
              "id": "module-2-l7-t1",
              "title": "Tổng quan",
              "lead": "Capstone tích hợp toàn bộ Module II thành một hệ thống multi-agent hoàn chỉnh: Planner + Researcher + Analyzer + Writer phối hợp theo pattern Hierarchical (Bài 6) với LangGraph, tái sử dụng RAG pipeline / vector store từ Module I - Capstone",
              "concept": "Capstone tích hợp toàn bộ Module II thành một hệ thống multi-agent hoàn chỉnh: Planner + Researcher + Analyzer + Writer phối hợp theo pattern Hierarchical (Bài 6) với LangGraph, tái sử dụng RAG pipeline / vector store từ Module I - Capstone làm retrieval tool cho Researcher.\nNội dung đang được biên soạn\nBài này sẽ bao gồm: kiến trúc chi tiết 4 agent, phần take-home (retry logic, parallelism, human-in-the-loop, custom MCP server cho Vietnamese news scraper), và quy trình đánh giá bằng LLM-as-judge trên trajectory.",
              "codeLang": "text",
              "code": "",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-2-l7-t2",
              "title": "Kiến trúc dự kiến",
              "lead": "mermaid",
              "concept": "",
              "codeLang": "mermaid",
              "code": "graph TD\n    subgraph Hierarchical Multi-Agent\n        PLAN[Planner] --> RES[Researcher]\n        PLAN --> ANA[Analyzer]\n        PLAN --> WRI[Writer]\n        RES --> PLAN\n        ANA --> PLAN\n        WRI --> PLAN\n    end\n\n    RES --> RAG[(Vector Store<br/>từ Module I Capstone)]\n    RES --> MCP[Custom MCP Server<br/>Vietnamese News Scraper]",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-2-l7-t3",
              "title": "Phụ thuộc",
              "lead": "- RAG pipeline & Vector DB (Module I, Bài 9) - tái sử dụng làm retrieval tool cho Researcher agent.",
              "concept": "- **RAG pipeline & Vector DB** (Module I, Bài 9) - tái sử dụng làm retrieval tool cho Researcher agent.\n- **LangGraph multi-agent** (Bài 6) - nền tảng cho kiến trúc Supervisor (Planner) + Workers.\n- **MCP** (Bài 4) - chuẩn để viết custom Vietnamese news scraper server.\n- **Agent Evaluation** (Bài 5) - LLM-as-judge cho trajectory evaluation.",
              "codeLang": "text",
              "code": "",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            }
          ]
        },
        {
          "id": "module-2-l8",
          "title": "Bài 8: Workshop + Mock Interview",
          "badge": "2 mục",
          "topics": [
            {
              "id": "module-2-l8-t1",
              "title": "Tổng quan",
              "lead": "Buổi tổng kết Module II: showcase capstone của học viên, phỏng vấn thử, và góc nhìn thực tế về thị trường AI Agent tại Việt Nam.",
              "concept": "Buổi tổng kết Module II: showcase capstone của học viên, phỏng vấn thử, và góc nhìn thực tế về thị trường AI Agent tại Việt Nam.\nNội dung đang được biên soạn\nBài này sẽ bao gồm: format Capstone Showcase (4 demo được chọn trước × 10 phút gồm demo + walkthrough + Q&A) và phần Guest Speaker về AI Agent Landscape in Vietnam 2026.",
              "codeLang": "text",
              "code": "",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-2-l8-t2",
              "title": "Cấu trúc dự kiến",
              "lead": "| Phần | Nội dung |",
              "concept": "| Phần | Nội dung |\n| --- | --- |\n| Capstone Showcase | 4 demo được chọn trước, mỗi demo 10 phút (demo + walkthrough + Q&A) |\n| Guest Speaker | AI Agent Landscape in Vietnam 2026 |",
              "codeLang": "text",
              "code": "",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            }
          ]
        }
      ]
    },
    {
      "id": "module-3",
      "title": "Module III: Production LLMOps",
      "badge": "8 bài",
      "icon": "⚙️",
      "lessons": [
        {
          "id": "module-3-l1",
          "title": "Bài 1: LLMOps Overview & Prompt Management",
          "badge": "8 mục",
          "topics": [
            {
              "id": "module-3-l1-t1",
              "title": "Tổng quan",
              "lead": "Bài này đặt nền cho toàn bộ Module III. Hai câu hỏi trung tâm:",
              "concept": "Bài này đặt nền cho toàn bộ Module III. Hai câu hỏi trung tâm:\n1. **LLMOps khác MLOps ở đâu?** Không có vòng lặp retrain, artifact chính không phải model weights mà là **prompt + config + eval set**.\n2. **Vì sao prompt cần được quản lý như code?** Prompt hardcode rải rác khiến không ai biết version nào đang chạy production, không rollback được, không A/B test được.\nSau bài này bạn sẽ có một **prompt registry** có versioning, load prompt theo version tại runtime, và chạy được A/B test prompt trên traffic thật.",
              "codeLang": "text",
              "code": "",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-3-l1-t2",
              "title": "1. LLMOps vs MLOps",
              "lead": "Cả hai đều là \"đưa mô hình vào production và giữ nó chạy tốt\": versioning artifact, test trước khi deploy, monitor sau khi deploy, có đường rollback.",
              "concept": "",
              "codeLang": "text",
              "code": "",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-3-l1-t3",
              "title": "2. Vì sao prompt cần được quản lý",
              "lead": "python",
              "concept": "Vấn đề khi hệ thống lớn lên:\n| Vấn đề | Hệ quả |\n| --- | --- |\n| Prompt trộn lẫn với code | Đổi 1 từ trong prompt = deploy lại toàn bộ service |\n| Không có version | \"Tuần trước chất lượng tốt hơn\" - không biết prompt đã đổi gì, không so được |\n| Copy-paste giữa nhiều service | Cùng một prompt tồn tại 4 bản hơi khác nhau, sửa chỗ này quên chỗ kia |\n| Không tách được người sửa | PM muốn chỉnh giọng văn phải nhờ engineer sửa code |\n| Không A/B test được | Muốn thử prompt mới phải deploy, không chạy song song 2 bản được |\n| Không rollback nhanh | Prompt mới gây hồi quy lúc 2h sáng - phải revert commit + build + deploy |\n### Nguyên tắc\n\\> **Prompt là artifact production, không phải hằng số trong code.** Nó cần: định danh, version, metadata, lịch sử thay đổi, và cơ chế load động.",
              "codeLang": "python",
              "code": "# rag_service.py - prompt nằm ngay trong code, giữa logic\ndef answer(question: str, context: str) -> str:\n    prompt = f\"\"\"Bạn là trợ lý pháp lý. Dựa vào tài liệu sau, trả lời câu hỏi.\nNếu không có thông tin, nói \"Tôi không tìm thấy\".\n\nTài liệu:\n{context}\n\nCâu hỏi: {question}\"\"\"\n    return llm(prompt)",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-3-l1-t4",
              "title": "3. Prompt Versioning & Templates",
              "lead": "Prompt sống trong file riêng (hoặc registry), code chỉ tham chiếu tên + version:",
              "concept": "Validate biến là bước rẻ nhất trong CI\n90% lỗi prompt production là \"quên truyền biến\" hoặc \"đổi tên biến trong template mà quên sửa code\". Một hàm `_required_vars()` + check ở [CI lint](https://handbook.yourclassacademy.com/llm-engineer/module-3/06-cicd/#4-ci-patterns-cho-llm) chặn được gần hết.\n### Metadata cần lưu cùng mỗi version\n- `model` target (prompt tối ưu cho model nào)\n- `owner` (ai chịu trách nhiệm)\n- `eval_score` gần nhất + link tới eval run\n- `changelog` (đổi gì so với version trước, **vì sao**)\n- `status`: `draft` / `staging` / `production` / `deprecated`",
              "codeLang": "yaml",
              "code": "# prompts/rag_answer/v2.yaml\nname: rag_answer\nversion: 2\nmodel: claude-sonnet-5\ndescription: \"Trợ lý pháp lý RAG - thêm ràng buộc trích dẫn điều luật\"\nowner: legal-team@company.com\ncreated: 2026-09-01\nchangelog: \"v1 -> v2: bắt buộc trích số điều luật; thêm câu từ chối khi thiếu context\"\neval_score: 0.87   # điểm eval subset gần nhất, xem Bài 2\ntemplate: |\n  Bạn là trợ lý pháp lý. Chỉ dùng thông tin trong <tai_lieu>.\n  Nếu không đủ thông tin, trả lời đúng câu: \"Tôi không tìm thấy thông tin này trong tài liệu.\"\n  Khi trích dẫn, ghi rõ số điều luật.\n\n  <tai_lieu>\n  {context}\n  </tai_lieu>\n\n  Câu hỏi: {question}",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-3-l1-t5",
              "title": "4. Prompt Registry",
              "lead": "Registry = nơi lưu tất cả prompt version + metadata, có API để code load theo tên/version, và (lý tưởng) có UI để so sánh.",
              "concept": "Registry = nơi lưu tất cả prompt version + metadata, có API để code load theo tên/version, và (lý tưởng) có UI để so sánh.\n### Hai hướng tiếp cận\n|  | Git-based | Hosted (LangSmith Prompt Hub / PromptLayer / Langfuse Prompts) |\n| --- | --- | --- |\n| **Nơi lưu** | File YAML/Jinja trong repo | Dịch vụ ngoài, có DB + UI |\n| **Version** | Git commit/tag | Version tự động trong hệ thống |\n| **Review** | Qua PR (diff rõ ràng, có CI) | Qua UI, một số hỗ trợ approval |\n| **Ai sửa được** | Ai biết Git (thường là engineer) | Cả non-engineer qua UI |\n| **Đổi prompt không deploy code?** | Không (trừ khi load động từ config store) | Có - app pull version mới lúc runtime |\n| **So sánh version** | `git diff` | UI side-by-side, có playground |\n| **Phụ thuộc bên ngoài** | Không | Có - registry down thì cần fallback cache |\n| **Phù hợp** | Team nhỏ, prompt gắn chặt code, muốn mọi thay đổi qua CI | Team có PM/nhiều người chỉnh prompt, cần đổi nhanh không qua deploy |\n### Interface tối thiểu của một registry\nDù chọn hướng nào, code chỉ nên thấy một interface:\n\nRegistry hosted cần fallback\nNếu load prompt qua API lúc runtime, một sự cố của registry = toàn bộ app chết. Luôn cache version `production` xuống đĩa/bộ nhớ và dùng bản cache khi API lỗi. Ghi log khi phải fallback.\n### Git-based registry: bố cục thư mục\n\nĐổi version production = sửa 1 dòng trong `production.txt` + PR. Rollback = revert PR đó.",
              "codeLang": "python",
              "code": "# prompt_registry/__init__.py\nfrom functools import lru_cache\n\nclass PromptRegistry:\n    def get(self, name: str, version: int | str = \"production\") -> \"Prompt\":\n        \"\"\"Lấy prompt theo tên + version.\n        version có thể là số cụ thể (2) hoặc alias (\"production\", \"staging\", \"latest\").\n        \"\"\"\n        ...\n\n    def render(self, name: str, version=\"production\", **vars) -> str:\n        p = self.get(name, version)\n        return render(p.template, **vars)\n\n@lru_cache\ndef registry() -> PromptRegistry:\n    # đọc từ file (git-based) hoặc khởi tạo client (hosted)\n    ...",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-3-l1-t6",
              "title": "5. Prompt A/B Testing",
              "lead": "Khi có prompt mới qua được [eval gate](https://handbook.yourclassacademy.com/llm-engineer/module-3/02-eval-pipelines/) nhưng bạn vẫn muốn kiểm chứng trên traffic thật trước khi rollout 100%.",
              "concept": "Khi có prompt mới qua được [eval gate](https://handbook.yourclassacademy.com/llm-engineer/module-3/02-eval-pipelines/) nhưng bạn vẫn muốn kiểm chứng trên **traffic thật** trước khi rollout 100%.\n### Traffic splitting\n\n### Nguyên tắc\n| Nguyên tắc | Vì sao |\n| --- | --- |\n| **Sticky assignment** theo `user_id` (không random mỗi request) | Trải nghiệm nhất quán; phân tích theo user mới đúng |\n| Bắt đầu nhỏ (5–10% treatment) | Giới hạn thiệt hại nếu prompt mới tệ hơn thực tế |\n| Định nghĩa **primary metric** trước khi chạy | Tránh \"p-hacking\" - nhìn 10 metric rồi chọn cái đẹp |\n| Theo dõi **guardrail metrics** | Prompt mới có thể tăng chất lượng nhưng tăng cost/latency/độ dài → phải chặn |\n| Chạy đủ lâu để có significance | Traffic thấp cần vài ngày; đừng kết luận sau 1 giờ |\n### Đọc kết quả\n- **Primary metric** (ví dụ: tỉ lệ thumbs-up, hoặc eval score trên sample production) - treatment có tốt hơn không, chênh lệch có ý nghĩa thống kê không.\n- **Guardrail**: cost/request, p95 latency, độ dài output trung bình - không được xấu đi quá ngưỡng.\n- Nếu treatment thắng cả primary lẫn guardrail → promote version đó thành `production`. Nếu không → giữ control, ghi lại bài học vào `changelog`.",
              "codeLang": "python",
              "code": "import hashlib\n\ndef pick_prompt_version(user_id: str, experiment: dict) -> int:\n    \"\"\"experiment = {\"control\": 2, \"treatment\": 3, \"treatment_pct\": 20}\n    Sticky theo user_id: cùng user luôn thấy cùng version.\n    \"\"\"\n    bucket = int(hashlib.sha256(user_id.encode()).hexdigest(), 16) % 100\n    if bucket < experiment[\"treatment_pct\"]:\n        return experiment[\"treatment\"]\n    return experiment[\"control\"]",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-3-l1-t7",
              "title": "6. Hands-on: Prompt registry cho Vietnamese RAG assistant",
              "lead": "Dùng lại assistant từ [Capstone Module I](https://handbook.yourclassacademy.com/llm-engineer/module-1/09-capstone/).",
              "concept": "Dùng lại assistant từ [Capstone Module I](https://handbook.yourclassacademy.com/llm-engineer/module-1/09-capstone/).\n### Bước 1 - Tách prompt ra file\n- Tạo `prompts/rag_answer/v1.yaml` với prompt hiện tại của capstone.\n- Viết `prompt_registry` tối thiểu (git-based): `get()`, `render()`, alias `production` đọc từ `production.txt`.\n- Thay chỗ hardcode trong service bằng `registry().render(\"rag_answer\", ...)`.\n### Bước 2 - Tạo version mới + diff\n- Tạo `v2.yaml`: thêm ràng buộc \"bắt buộc trích số điều luật\" và câu từ chối chuẩn khi thiếu context.\n- `git diff` giữa v1 và v2. Điền `changelog` giải thích **vì sao** đổi.\n### Bước 3 - So sánh hai version\n- Lấy 5 câu hỏi từ tài liệu pháp lý.\n- Chạy assistant với `version=1` rồi `version=2`, in output cạnh nhau.\n- Ghi nhận: v2 có luôn trích điều luật không? Có từ chối đúng khi hỏi ngoài tài liệu không?\n### Bước 4 (mở rộng) - A/B scaffold\n- Thêm `pick_prompt_version()` với `treatment_pct=50`.\n- Log version đã chọn cho mỗi request. Chạy 20 câu hỏi, xác nhận phân bổ \\~50/50 và sticky theo `user_id`.\n### Tiêu chí hoàn thành\n- \\[ \\] Không còn prompt hardcode trong service\n- \\[ \\] Có ≥ 2 version với `changelog` và metadata đầy đủ\n- \\[ \\] Đổi version production chỉ bằng sửa `production.txt` + không cần sửa code\n- \\[ \\] Rollback = revert 1 commit\n- \\[ \\] Có script so sánh output giữa 2 version",
              "codeLang": "text",
              "code": "",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-3-l1-t8",
              "title": "Tóm tắt",
              "lead": "| Khái niệm | Cốt lõi |",
              "concept": "| Khái niệm | Cốt lõi |\n| --- | --- |\n| LLMOps vs MLOps | Không retrain; artifact là prompt+config; vòng lặp tính bằng giờ |\n| Prompt versioning | Semantic version + changelog giải thích \"vì sao\"; validate biến trong CI |\n| Prompt registry | Git-based (mọi thay đổi qua PR) vs Hosted (đổi nhanh, cần fallback cache) |\n| Registry interface | Code chỉ thấy `get(name, version)` / `render(...)`; alias `production` |\n| A/B testing | Sticky theo user_id; primary + guardrail metrics; bắt đầu nhỏ |",
              "codeLang": "text",
              "code": "",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            }
          ]
        },
        {
          "id": "module-3-l2",
          "title": "Bài 2: LLM Evaluation Pipelines",
          "badge": "9 mục",
          "topics": [
            {
              "id": "module-3-l2-t1",
              "title": "Tổng quan",
              "lead": "Module I, Bài 7 dạy cách chấm điểm một output: BLEU/ROUGE, BERTScore, LLM-as-judge (và 6 bias của nó), RAGAS. Module II, Bài 5 mở rộng sang trajectory - chuỗi hành động của agent.",
              "concept": "Module I, Bài 7 dạy *cách chấm điểm một output*: BLEU/ROUGE, BERTScore, LLM-as-judge (và 6 bias của nó), RAGAS. Module II, Bài 5 mở rộng sang *trajectory* - chuỗi hành động của agent.\nBài này biến những kỹ thuật đó thành một **pipeline chạy tự động**:\n- **Golden dataset** được version hoá, curate, chống leak.\n- **Eval runner** chạy app trên toàn bộ dataset, cho điểm, lưu lịch sử.\n- **Regression gate** so điểm với baseline và phân biệt hồi quy thật với noise.\n- **CI integration**: eval subset chặn merge trên mỗi PR (Bài 6).",
              "codeLang": "text",
              "code": "",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-3-l2-t2",
              "title": "1. Vì sao eval LLM khác eval ML",
              "lead": "|  | ML truyền thống | LLM app |",
              "concept": "|  | ML truyền thống | LLM app |\n| --- | --- | --- |\n| Đầu ra | Nhãn/số - so khớp trực tiếp | Văn bản tự do - nhiều đáp án đúng |\n| Tính lặp lại | Deterministic (cùng input → cùng output) | Non-deterministic (temperature, provider) |\n| Metric | accuracy, F1, AUC - ổn định | LLM-as-judge - bản thân judge cũng nhiễu |\n| Regression | Thấy rõ qua metric tụt | **Vô hình**: đổi model hoặc sửa 1 câu prompt làm hỏng 1 nhóm case, metric tổng vẫn ổn |\n| Test suite | Unit test đủ tin | Cần dataset + judge; \"pass/fail\" là ngưỡng, không tuyệt đối |\n**Regression vô hình - ví dụ điển hình**\nBạn siết prompt để giảm hallucination. Eval tổng: 0.86 → 0.87 (tưởng như tốt hơn). Nhưng nhóm câu hỏi \"so sánh hai điều luật\" tụt từ 0.9 → 0.6 vì prompt mới khiến model từ chối trả lời khi câu hỏi cần tổng hợp nhiều nguồn. **Chỉ eval theo nhóm (slice) mới bắt được.**",
              "codeLang": "text",
              "code": "",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-3-l2-t3",
              "title": "2. Golden Dataset",
              "lead": "Golden dataset (golden set) = tập câu hỏi + đáp án/tiêu chí kỳ vọng, được chọn lọc kỹ, dùng làm thước đo chuẩn.",
              "concept": "Golden dataset (golden set) = tập câu hỏi + đáp án/tiêu chí kỳ vọng, được chọn lọc kỹ, dùng làm thước đo chuẩn.\n### Build - nguồn dữ liệu\n\n| Nguồn | Ưu | Nhược |\n| --- | --- | --- |\n| **Log production** | Phân bố đúng thực tế, câu hỏi tự nhiên | Cần lọc PII; chưa có đáp án chuẩn, phải gán tay |\n| **Tự sinh từ tài liệu** | Nhanh, có ngay ground truth từ đoạn nguồn | Câu hỏi \"sách vở\", không giống người dùng hỏi |\n| **Synthetic (LLM sinh)** | Phủ nhanh nhiều biến thể (diễn đạt khác, sai chính tả) | Dễ trùng phân bố của model sinh; phải người review |\n| **Case lỗi đã gặp** | Chống tái hồi quy - giá trị cao nhất | Tích luỹ dần theo thời gian, không có sẵn từ đầu |\n### Curate\n- **Đa dạng slice**: đánh nhãn mỗi case (`loại câu hỏi`, `độ khó`, `cần multi-hop?`, `ngoài phạm vi?`). Slice là thứ giúp bắt regression vô hình.\n- **Edge case có chủ đích**: câu hỏi ngoài tài liệu (kỳ vọng: từ chối), câu mơ hồ (kỳ vọng: hỏi lại), câu có prompt injection (kỳ vọng: bỏ qua).\n- **Cân bằng**: đừng để 80% case là \"tra cứu 1 điều luật\" - production không như vậy.\n### Maintain\n\n| Quy tắc maintain | Vì sao |\n| --- | --- |\n| **Version hoá dataset** (như prompt) | So điểm giữa các lần chạy phải trên cùng dataset version |\n| **Chống leak** | Không để case eval (đặc biệt câu hỏi hiếm) lọt vào few-shot/context của prompt → điểm ảo cao |\n| **Review khi thêm case** | Mỗi case là một \"định nghĩa đúng\"; sai một case = sai thước đo mãi mãi |\n| **Mỗi regression → +1 case** | Golden set lớn dần theo đúng những chỗ hệ thống từng sai |\n| **Giữ kích thước hợp lý** | Full set 100–300 case chạy nightly; subset 20–40 case chạy trên PR |",
              "codeLang": "mermaid",
              "code": "graph LR\n    LOG[Log production<br/>câu hỏi thật] --> DS[(Golden Set)]\n    DOC[Trích từ tài liệu nguồn<br/>tự sinh Q&A] --> DS\n    SYN[Synthetic<br/>LLM sinh biến thể] --> DS\n    BUG[Case lỗi đã gặp<br/>hồi quy trước đây] --> DS",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-3-l2-t4",
              "title": "3. Eval Methods: chọn cái nào",
              "lead": "Không phải mọi case cần LLM-as-judge. Xếp tầng từ rẻ đến đắt:",
              "concept": "Không phải mọi case cần LLM-as-judge. Xếp tầng từ rẻ đến đắt:\n\n| Method | Chi phí | Độ tin | Tốc độ | Dùng cho |\n| --- | --- | --- | --- | --- |\n| **Rule-based assertion** | \\~0 | Cao (nếu rule đúng) | Tức thì | Format JSON hợp lệ, `must_include` / `must_not_include`, độ dài, regex số điều luật, không rỗng |\n| **LLM-as-judge (rubric)** | Trung bình | Trung bình | Trung bình | Tính đúng ngữ nghĩa, đầy đủ, rõ ràng, đúng giọng |\n| **RAGAS** | Trung bình | Trung bình | Chậm | Faithfulness, answer relevancy, context precision/recall |\n| **Human** | Cao | Cao nhất | Rất chậm | Chuẩn hoá judge (đối chiếu định kỳ), phân xử case khó |\n### Rule-based - viết trước, viết nhiều",
              "codeLang": "mermaid",
              "code": "graph TB\n    C[Case] --> R{Có kiểm được<br/>bằng rule?}\n    R -->|Có| RULE[Rule-based assertion<br/>~0đ, tức thì]\n    R -->|Không| RAG{Là RAG<br/>faithfulness?}\n    RAG -->|Có| RAGAS[RAGAS]\n    RAG -->|Không| JUDGE[LLM-as-judge<br/>theo rubric]\n    JUDGE --> HUMAN{Case tranh cãi /<br/>chuẩn hoá judge?}\n    HUMAN -->|Có| H[Human review<br/>đắt, chậm, chuẩn nhất]",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-3-l2-t5",
              "title": "4. Từ eval thủ công sang eval pipeline",
              "lead": "mermaid",
              "concept": "",
              "codeLang": "mermaid",
              "code": "graph LR\n    DS[(Golden Set vN)] --> RUN[Runner<br/>chạy app cho từng case]\n    RUN --> OUT[Outputs]\n    OUT --> SC[Scorers<br/>rules + judge + RAGAS]\n    SC --> AGG[Aggregate<br/>tổng + theo slice]\n    AGG --> REP[Report<br/>markdown / JSON]\n    AGG --> HIST[(History<br/>điểm theo commit/prompt-version)]",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-3-l2-t6",
              "title": "5. Regression Testing",
              "lead": "Đặt baseline từ phiên bản chuẩn, với droptolerance để tránh chặn merge do noise.",
              "concept": "",
              "codeLang": "python",
              "code": "# eval/gate.py\nGATES = {\n    \"overall\":        {\"baseline\": 0.85, \"drop_tolerance\": 0.03},\n    \"rule_pass_rate\": {\"baseline\": 0.95, \"drop_tolerance\": 0.02},\n    \"slice:injection\":{\"baseline\": 0.90, \"drop_tolerance\": 0.05},  # slice quan trọng có gate riêng\n}\n\ndef check_gate(summary: dict) -> tuple[bool, list[str]]:\n    fails = []\n    for metric, cfg in GATES.items():\n        val = _lookup(summary, metric)\n        if val is None:\n            continue\n        if val < cfg[\"baseline\"] - cfg[\"drop_tolerance\"]:\n            fails.append(f\"{metric}: {val:.3f} < {cfg['baseline']} - {cfg['drop_tolerance']}\")\n    return (len(fails) == 0, fails)",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-3-l2-t7",
              "title": "6. CI Integration: Eval Gate",
              "lead": "| Khi nào | Chạy gì | Ràng buộc |",
              "concept": "",
              "codeLang": "yaml",
              "code": "# .github/workflows/eval-gate.yml\nname: eval-gate\non:\n  pull_request:\n    paths: [\"prompts/**\", \"src/rag/**\", \"eval/**\"]\njobs:\n  eval:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n      - uses: actions/setup-python@v5\n        with: { python-version: \"3.12\" }\n      - run: pip install -r requirements.txt\n      - name: Run eval subset\n        env:\n          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}\n          EVAL_CACHE: \".eval_cache\"        # cache response để không đốt tiền lặp lại\n        run: python -m eval.run --dataset eval/datasets/legal_qa/v3.yaml --subset --report eval_report.md\n      - name: Check gate\n        run: python -m eval.gate --run eval_report.json   # exit 1 nếu fail -> chặn merge\n      - name: Comment report on PR\n        if: always()\n        uses: actions/github-script@v7\n        with:\n          script: |\n            const fs = require('fs');\n            const body = fs.readFileSync('eval_report.md', 'utf8');\n            github.rest.issues.createComment({ ...context.repo, issue_number: context.issue.number, body });",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-3-l2-t8",
              "title": "7. Hands-on: Vietnamese eval dataset 30 case + LLM-as-judge pipeline",
              "lead": "- 18 case lookup (tra 1 điều luật) - có expected + mustinclude.",
              "concept": "",
              "codeLang": "text",
              "code": "",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-3-l2-t9",
              "title": "Tóm tắt",
              "lead": "mermaid",
              "concept": "| Khái niệm | Cốt lõi |\n| --- | --- |\n| Regression vô hình | Số tổng ổn nhưng 1 slice tụt → luôn eval theo slice |\n| Golden set | Version hoá, chống leak, mỗi regression thêm 1 case |\n| Chọn method | Rule-based trước (rẻ, tin) → judge theo rubric → RAGAS → human spot-check |\n| Pipeline | Runner (song song) → scorers → aggregate → report + history |\n| Noise vs regression | Đo variance nền, đặt tolerance \\> variance, xem case-level |\n| Eval gate | Subset chặn PR (\\< 3 phút, cache response); full chạy nightly |",
              "codeLang": "mermaid",
              "code": "graph LR\n    SRC[Log prod + tài liệu + synthetic + case lỗi] --> GS[(Golden Set vN<br/>có slice, chống leak)]\n    GS --> RUN[Runner chạy app]\n    RUN --> SC[Rules -> RAGAS -> Judge -> Human]\n    SC --> AGG[Aggregate: tổng + theo slice]\n    AGG --> GATE{So baseline<br/>vượt tolerance?}\n    GATE -->|Trong tolerance| PASS[Merge được]\n    GATE -->|Vượt| FAIL[Chặn merge + report case fail]\n    AGG --> HIST[(History điểm theo version)]",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            }
          ]
        },
        {
          "id": "module-3-l3",
          "title": "Bài 3: Cost Optimization & Caching",
          "badge": "10 mục",
          "topics": [
            {
              "id": "module-3-l3-t1",
              "title": "Tổng quan",
              "lead": "Module I, Bài 8 đã giới thiệu ba đòn bẩy: prompt caching, semantic caching, model routing (rule-based / embedding / classifier). Bài này mở rộng sang cấp hệ thống:",
              "concept": "Module I, Bài 8 đã giới thiệu ba đòn bẩy: prompt caching, semantic caching, model routing (rule-based / embedding / classifier). Bài này **mở rộng sang cấp hệ thống**:\n- Hiểu **token economics**: tiền đi đâu, vì sao context bloat là kẻ giết ngân sách.\n- **Đo trước khi tối ưu**: cost per request / user / feature.\n- **Cache 2 tầng** hoàn chỉnh với invalidation đúng theo prompt version.\n- **Model cascading** (khác routing) và **Batch API**.\n- **Cost governance**: budget, alert, hard limit.",
              "codeLang": "text",
              "code": "",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-3-l3-t2",
              "title": "1. Token Economics",
              "lead": "mermaid",
              "concept": "| Yếu tố | Đặc điểm chi phí |\n| --- | --- |\n| **Input tokens** | Rẻ hơn; với prompt caching còn rẻ nữa (–50→90% cho phần cache hit) |\n| **Output tokens** | Đắt nhất - thường 3–5× giá input. Reasoning model \"nghĩ\" nhiều = tốn nhiều output ẩn |\n| **Context bloat** | RAG lấy 10 chunk khi 3 chunk là đủ; lịch sử 20 lượt khi 4 lượt là đủ; tool schema JSON lặp lại mỗi request |\n| **Retry / self-reflection** | Mỗi vòng lặp agent là một request đầy đủ - nhân chi phí |\n### Công thức nhẩm\n\nTrước khi tối ưu: đo phân bố token\nLog `input_tokens`, `output_tokens`, và **breakdown** (bao nhiêu cho context, cho history, cho system). Thường phát hiện: 1 tính năng ít dùng nhưng context khổng lồ đang ngốn 40% hoá đơn.",
              "codeLang": "mermaid",
              "code": "graph LR\n    subgraph \"Input tokens (rẻ hơn)\"\n        SYS[\"System prompt\"] --- FS[\"Few-shot\"] --- CTX[\"RAG context\"] --- HIST[\"Lịch sử hội thoại\"] --- Q[\"Câu hỏi\"]\n    end\n    subgraph \"Output tokens (đắt 3-5x)\"\n        ANS[\"Câu trả lời\"] --- REASON[\"Reasoning / chain-of-thought\"]\n    end",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-3-l3-t3",
              "title": "2. Đo trước khi tối ưu",
              "lead": "python",
              "concept": "",
              "codeLang": "python",
              "code": "# cost/tracker.py\nimport tiktoken\nPRICING = {  # USD / 1M tokens (minh hoạ - luôn tra bảng giá hiện hành)\n    \"claude-sonnet-5\": {\"in\": 3.0, \"out\": 15.0},\n    \"gpt-4o-mini\":     {\"in\": 0.15, \"out\": 0.60},\n}\n\ndef record_cost(*, feature: str, user_id: str, model: str,\n                usage, cache_hit: bool = False):\n    p = PRICING[model]\n    cost = usage.prompt_tokens / 1e6 * p[\"in\"] + usage.completion_tokens / 1e6 * p[\"out\"]\n    metrics.emit(\"llm_cost_usd\", cost, tags={\n        \"feature\": feature, \"model\": model,\n        \"cache\": \"hit\" if cache_hit else \"miss\",\n    })\n    metrics.emit(\"llm_tokens_in\", usage.prompt_tokens, tags={\"feature\": feature})\n    metrics.emit(\"llm_tokens_out\", usage.completion_tokens, tags={\"feature\": feature})\n    # per-user: dùng cho hard limit (mục 7), không cần gửi hết lên dashboard\n    redis.incrbyfloat(f\"cost:user:{user_id}:{today()}\", cost)",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-3-l3-t4",
              "title": "3. Caching tầng 1: Exact / Prompt Cache",
              "lead": "Cơ chế đã học ở [M1, Bài 8](https://handbook.yourclassacademy.com/llm-engineer/module-1/08-production-optimization/#2-prompt-caching): provider cache phần prefix lặp lại. Điểm mở rộng cho production:",
              "concept": "Invalidation: prompt_version phải nằm trong cache key\nNếu bạn promote `rag_answer` v2 → v3 ([Bài 1](https://handbook.yourclassacademy.com/llm-engineer/module-3/01-llmops-prompt-mgmt/)) mà cache key không chứa version, người dùng vẫn nhận câu trả lời sinh bởi v2 trong suốt TTL. Đưa `prompt_version` (và `model`) vào key → version mới tự động là \"cache namespace\" mới, bản cũ hết hạn tự nhiên.",
              "codeLang": "python",
              "code": "# cache/exact.py\ndef cache_key(prompt_name: str, prompt_version: int, model: str,\n              rendered_prompt: str, params: dict) -> str:\n    raw = json.dumps({\n        \"pn\": prompt_name, \"pv\": prompt_version, \"m\": model,\n        \"p\": rendered_prompt, \"params\": params,\n    }, sort_keys=True, ensure_ascii=False)\n    return \"resp:\" + hashlib.sha256(raw.encode()).hexdigest()\n\ndef get_or_call(prompt_name, prompt_version, model, rendered_prompt, params, call_fn):\n    key = cache_key(prompt_name, prompt_version, model, rendered_prompt, params)\n    if (hit := redis.get(key)) is not None:\n        record_cost(feature=..., model=model, usage=ZERO_USAGE, cache_hit=True)\n        return json.loads(hit)\n    out = call_fn()\n    redis.setex(key, ttl=86400, value=json.dumps(out))\n    return out",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-3-l3-t5",
              "title": "4. Caching tầng 2: Semantic Cache",
              "lead": "Trả lời cũ cho câu hỏi gần giống (không cần giống hệt). Cơ chế đã học ở [M1, Bài 8](https://handbook.yourclassacademy.com/llm-engineer/module-1/08-production-optimization/#3-semantic-caching). Bổ sung cho production:",
              "concept": "Trả lời cũ cho câu hỏi **gần giống** (không cần giống hệt). Cơ chế đã học ở [M1, Bài 8](https://handbook.yourclassacademy.com/llm-engineer/module-1/08-production-optimization/#3-semantic-caching). Bổ sung cho production:\n### Kiến trúc\n\nSemantic cache chỉ đáng khi `hit_rate` đủ cao (FAQ, support bot: 20–40%; câu hỏi đa dạng: có thể \\< 5% → không đáng phức tạp).",
              "codeLang": "mermaid",
              "code": "graph LR\n    Q[\"Câu hỏi mới\"] --> EMB[\"Embed\"]\n    EMB --> SEARCH[\"Vector search trong cache store\"]\n    SEARCH --> SIM{\"Similarity ≥ ngưỡng?\"}\n    SIM -->|Có| HIT[\"Trả lời cache - $0, ~10ms\"]\n    SIM -->|Không| LLM[\"Gọi LLM\"]\n    LLM --> STORE[\"Lưu embedding + câu trả lời vào cache\"]",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-3-l3-t6",
              "title": "5. Model Routing & Cascading",
              "lead": "mermaid",
              "concept": "|  | Routing | Cascading |\n| --- | --- | --- |\n| Quyết định | Trước khi gọi model, dựa trên **query** | Sau câu trả lời của model rẻ, dựa trên **output** |\n| Chi phí thêm | 1 lần phân loại (\\~ms) | Với case khó: trả tiền **cả hai** model |\n| Rủi ro | Phân loại sai → model rẻ nhận câu khó | Model rẻ \"tự tin sai\" → không escalate |\n| Khi nào tốt | Phân biệt dễ/khó rõ ràng từ query | Khó đoán độ khó trước; có tín hiệu chất lượng trên output |\n### Cascade implementation\n\n> Đo **tỉ lệ escalate**. Nếu 70% case phải escalate → cascade đang lỗ (trả 2 lần tiền cho phần lớn traffic); chuyển sang routing hoặc dùng thẳng model mạnh.",
              "codeLang": "mermaid",
              "code": "graph TB\n    subgraph \"Routing - quyết định TRƯỚC\"\n        Q1[\"Query\"] --> CLF[\"Phân loại: dễ / khó\"]\n        CLF -->|dễ| S1[\"Model rẻ\"]\n        CLF -->|khó| B1[\"Model mạnh\"]\n    end\n    subgraph \"Cascading - thử rồi ESCALATE\"\n        Q2[\"Query\"] --> S2[\"Model rẻ trả lời\"]\n        S2 --> CHK{\"Đạt ngưỡng tin cậy /<br>qua guardrail?\"}\n        CHK -->|Có| DONE2[\"Dùng luôn\"]\n        CHK -->|Không| B2[\"Escalate: Model mạnh trả lại\"]\n    end",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-3-l3-t7",
              "title": "6. Kỹ thuật khác",
              "lead": "| Kỹ thuật | Cách làm | Lưu ý |",
              "concept": "",
              "codeLang": "python",
              "code": "# batch/submit.py\nbatch_input = [\n    {\"custom_id\": c[\"id\"], \"method\": \"POST\", \"url\": \"/v1/chat/completions\",\n     \"body\": {\"model\": \"gpt-4o-mini\", \"messages\": build_messages(c)}}\n    for c in cases\n]\n# ghi JSONL, upload, tạo batch job, poll trạng thái, tải kết quả",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-3-l3-t8",
              "title": "7. Cost Governance",
              "lead": "python",
              "concept": "",
              "codeLang": "python",
              "code": "# cost/budget.py\nMONTHLY_BUDGET_USD = 800\nALERT_THRESHOLDS = [0.5, 0.8, 1.0]   # 50% / 80% / 100%\n\ndef check_budget():\n    spent = sum_month_to_date()          # từ metrics store\n    projected = spent / days_elapsed() * days_in_month()\n    for t in ALERT_THRESHOLDS:\n        if spent >= MONTHLY_BUDGET_USD * t and not alerted(t):\n            alert(f\"Chi phí LLM đạt {t:.0%} ngân sách tháng \"\n                  f\"(${spent:.0f}/${MONTHLY_BUDGET_USD}). Dự phóng cuối tháng: ${projected:.0f}.\")\n            mark_alerted(t)",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-3-l3-t9",
              "title": "8. Hands-on: Cache 2 tầng cho Vietnamese chatbot",
              "lead": "Dùng chatbot RAG từ [Capstone Module I](https://handbook.yourclassacademy.com/llm-engineer/module-1/09-capstone/).",
              "concept": "Dùng chatbot RAG từ [Capstone Module I](https://handbook.yourclassacademy.com/llm-engineer/module-1/09-capstone/).\n### Bước 1 - Đo baseline\n- Chuẩn bị tập replay: 200 câu hỏi (trộn \\~30% trùng/gần giống để mô phỏng FAQ).\n- Gắn `record_cost()` vào đường gọi LLM. Chạy replay **không cache**.\n- Ghi: tổng cost, cost/request p50/p99, token in/out trung bình, breakdown context.\n### Bước 2 - Tầng 1: exact response cache\n- `cache_key` gồm `prompt_name`, `prompt_version`, `model`, `rendered_prompt`, `params`.\n- Redis `setex` TTL 24h. Chạy lại replay → đo hit rate, cost mới.\n- Bump prompt version → xác nhận cache tự \"reset\" (không trả câu cũ).\n### Bước 3 - Tầng 2: semantic cache\n- Embed câu hỏi (sau bước rewrite → standalone), vector store nhỏ (FAISS/Redis).\n- Ngưỡng khởi đầu 0.93; chạy replay, soát 10 hit ngẫu nhiên xem có false hit.\n- Tune ngưỡng; loại câu có tham số ngày/số khỏi semantic cache.\n### Bước 4 - Báo cáo\n| Cấu hình | Tổng cost | Cost/req | Hit rate | Ghi chú |\n| --- | --- | --- | --- | --- |\n| Không cache | ... | ... | – | baseline |\n| • Tầng 1 | ... | ... | ...% |  |\n| • Tầng 1 & 2 | ... | ... | ...% | false hit: .../10 |\n### Bước 5 (mở rộng) - Cascade\n- Thêm `answer_cascade()`: `gpt-4o-mini` trước, escalate sang `claude-sonnet-5` khi output nói \"không tìm thấy\" hoặc self-rating \\< 4.\n- Chạy replay (cache miss only), đo tỉ lệ escalate + cost so với dùng thẳng model mạnh.\n### Tiêu chí hoàn thành\n- [ ] Có số cost baseline với breakdown token\n- [ ] Cache key chứa `prompt_version` → bump version không trả câu cũ\n- [ ] Semantic cache có kiểm false hit thủ công + ngưỡng đã tune\n- [ ] Bảng so sánh cost trước/sau trên **cùng** tập replay\n- [ ] (Mở rộng) tỉ lệ escalate của cascade \\< 50% hoặc kết luận rõ cascade không đáng",
              "codeLang": "text",
              "code": "",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-3-l3-t10",
              "title": "Tóm tắt",
              "lead": "mermaid",
              "concept": "| Kỹ thuật | Khi nào dùng |\n| --- | --- |\n| Đo token/cost per feature | **Luôn**  • trước mọi tối ưu |\n| Prompt caching (provider) | Prefix dài lặp lại; sắp xếp tĩnh→động |\n| Exact response cache | Input lặp lại y hệt; key phải chứa prompt_version + model |\n| Semantic cache | FAQ/support, hit rate \\> \\~20%; ngưỡng cao + loại câu có tham số |\n| Routing | Phân biệt dễ/khó rõ từ query |\n| Cascading | Khó đoán độ khó trước; theo dõi tỉ lệ escalate |\n| Batch API | Workload offline (eval, backfill) - giảm \\~50% giá |\n| Budget + hard limit | Alert theo % ngân sách; cap ngày per user; cost spike = incident |",
              "codeLang": "mermaid",
              "code": "graph TB\n    REQ[\"Request\"] --> T1{\"Tầng 1<br>exact cache?\"}\n    T1 -->|hit| DONE[\"Trả lời - $0\"]\n    T1 -->|miss| T2{\"Tầng 2<br>semantic cache?\"}\n    T2 -->|hit| DONE\n    T2 -->|miss| ROUTE[\"Routing / Cascade\"]\n    ROUTE --> CALL[\"Gọi LLM<br>prompt tĩnh trước, động sau -> prompt cache\"]\n    CALL --> REC[\"record_cost per feature/user\"] --> STORE[\"Ghi vào 2 tầng cache\"]\n    REC --> BUD{\"Budget / hard limit\"}",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            }
          ]
        },
        {
          "id": "module-3-l4",
          "title": "Bài 4: Containerisation & LLM Serving",
          "badge": "7 mục",
          "topics": [
            {
              "id": "module-3-l4-t1",
              "title": "Tổng quan",
              "lead": "[Module I, Bài 2](https://handbook.yourclassacademy.com/llm-engineer/module-1/02-local-llms/llm-serving/) đã dạy chạy model local với Ollama và quantization (GGUF, AWQ...). Bài này chuyển sang serving cho production:",
              "concept": "[Module I, Bài 2](https://handbook.yourclassacademy.com/llm-engineer/module-1/02-local-llms/llm-serving/) đã dạy chạy model local với Ollama và quantization (GGUF, AWQ...). Bài này chuyển sang **serving cho production**:\n- Đóng gói LLM app bằng **Docker** đúng cách (multi-stage, không nhét weights vào image, GPU support).\n- **vLLM / TGI** cho throughput cao: **PagedAttention** và **continuous batching** giải quyết bài toán gì.\n- Chọn serving stack: Ollama vs vLLM/TGI vs API provider.\n- **FastAPI patterns** cho LLM: streaming SSE, async concurrency, xử lý rate limit.",
              "codeLang": "text",
              "code": "",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-3-l4-t2",
              "title": "1. Docker cho LLM App",
              "lead": "| Nguyên tắc | Vì sao |",
              "concept": "**Image GPU rất nặng** — Base CUDA + torch + vLLM dễ vượt 8–10 GB. Dùng `-runtime-` chứ không `-devel-`, xoá cache pip/apt trong cùng layer, cân nhắc multi-stage kể cả cho image GPU.",
              "codeLang": "docker",
              "code": "# ---------- build stage ----------\nFROM python:3.12.4-slim AS build\nWORKDIR /app\nRUN pip install --no-cache-dir uv\nCOPY requirements.txt .\nRUN uv pip install --system --no-cache -r requirements.txt\n\n# ---------- runtime stage ----------\nFROM python:3.12.4-slim AS runtime\nRUN useradd -m -u 1000 appuser\nWORKDIR /app\nCOPY --from=build /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages\nCOPY --from=build /usr/local/bin /usr/local/bin\nCOPY src/ ./src/\nCOPY prompts/ ./prompts/\n# Weights / vector index KHÔNG copy vào đây - mount volume hoặc tải lúc khởi động\nUSER appuser\nEXPOSE 8000\nHEALTHCHECK --interval=30s --timeout=5s --retries=3 \\\n  CMD python -c \"import urllib.request; urllib.request.urlopen('http://localhost:8000/health')\"\nCMD [\"uvicorn\", \"src.main:app\", \"--host\", \"0.0.0.0\", \"--port\", \"8000\", \"--workers\", \"2\"]",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-3-l4-t3",
              "title": "2. Self-hosted Serving: vLLM & TGI",
              "lead": "Khi bạn tự host model (không gọi API provider), throughput là bài toán chính: nhiều request đồng thời trên GPU có hạn.",
              "concept": "Khi bạn tự host model (không gọi API provider), throughput là bài toán chính: nhiều request đồng thời trên GPU có hạn.\n### Vấn đề 1: KV cache phân mảnh → PagedAttention\nMỗi token sinh ra cần lưu **key/value** của tất cả token trước đó (KV cache). Cách naive: cấp trước một khối bộ nhớ liên tục bằng `max_length` cho mỗi request → lãng phí lớn (request ngắn vẫn chiếm chỗ dài) và phân mảnh.\n**PagedAttention** (vLLM) quản lý KV cache như **phân trang bộ nhớ ảo của OS**: chia thành các block nhỏ cố định, cấp phát theo nhu cầu, block không cần liên tục. Kết quả:\n- Tận dụng \\~96% bộ nhớ KV (so với \\~20–40% cách naive).\n- Cho phép nhiều request đồng thời hơn trên cùng GPU → throughput cao hơn nhiều lần.\n- Chia sẻ block giữa các request có chung prefix (prompt caching cấp GPU).\n### Vấn đề 2: batch tĩnh lãng phí → Continuous Batching\n\n**Continuous batching** (còn gọi in-flight batching): lập lịch ở mức **iteration** (mỗi bước sinh 1 token) thay vì mức request. Request kết thúc sẽ nhường slot cho request đang chờ ngay lập tức → GPU không idle.\n### vLLM - chạy nhanh\n\n### TGI (Text Generation Inference - HuggingFace)\nTương đương vLLM về ý tưởng (paged/flash attention, continuous batching), đóng gói Docker sẵn, tích hợp tốt hệ sinh thái HF.",
              "codeLang": "mermaid",
              "code": "graph TB\n    subgraph \"Static batching\"\n        S1[Chờ đủ N request] --> S2[Chạy cả batch tới khi request DÀI NHẤT xong] --> S3[Request ngắn ngồi chờ vô ích]\n    end\n    subgraph \"Continuous batching\"\n        C1[Request xong -> rời batch ngay] --> C2[Chèn request mới vào slot trống ngay lập tức] --> C3[GPU luôn bận]\n    end",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-3-l4-t4",
              "title": "3. Chọn Serving Stack",
              "lead": "|  | Ollama | vLLM / TGI | API provider |",
              "concept": "|  | Ollama | vLLM / TGI | API provider |\n| --- | --- | --- | --- |\n| Mục đích | Dev, demo, máy cá nhân | Production self-host, throughput cao | Production, không quản hạ tầng |\n| Throughput đồng thời | Thấp | Rất cao (PagedAttention + continuous batching) | Cao (provider lo) |\n| Cần GPU? | Không bắt buộc (chạy CPU/GGUF được) | Có (thực tế bắt buộc) | Không |\n| Chi phí | Điện + phần cứng | GPU (thuê/mua) - đáng khi volume lớn | Per token - đáng khi volume vừa/nhỏ |\n| Vận hành | Rất nhẹ | Nặng (GPU driver, OOM, autoscale) | Nhẹ nhất |\n| Model | Open-weights | Open-weights | Model của provider (+ một số open qua Vertex/Bedrock) |\n| Khi nào chọn | Học, thử nghiệm | \\> \\~vài triệu token/ngày, hoặc bắt buộc on-prem | Mặc định để bắt đầu; volume chưa lớn |\n**Đừng self-host quá sớm** — Chi phí thật của vLLM không phải tiền GPU mà là **thời gian vận hành**: driver, CUDA mismatch, OOM lúc burst, autoscale GPU. Bắt đầu bằng API provider; chuyển self-host khi phép tính token cho thấy tiết kiệm đủ bù chi phí vận hành.",
              "codeLang": "text",
              "code": "",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-3-l4-t5",
              "title": "4. FastAPI Patterns cho LLM",
              "lead": "Người dùng muốn thấy token xuất hiện dần thay vì chờ 5 giây rồi hiện cả đoạn.",
              "concept": "- Dùng client **async** (`AsyncOpenAI`, `httpx.AsyncClient`) - đừng gọi SDK sync trong endpoint async (block event loop).\n- Nhiều `uvicorn --workers` cho CPU-bound (parse, embed); async lo I/O-bound (chờ LLM).\n### Xử lý rate limit từ provider\n\n| Vấn đề | Xử lý |\n| --- | --- |\n| `429 RateLimitError` | Exponential backoff + jitter; tôn trọng header `Retry-After` nếu có |\n| Timeout | Đặt timeout rõ ràng (30–60s); huỷ khi client disconnect |\n| Burst vượt quota | Semaphore giới hạn concurrency; hàng đợi có giới hạn + trả 503 khi đầy |\n| Provider outage | Fallback model/provider (xem [Bài 7](https://handbook.yourclassacademy.com/llm-engineer/module-3/07-observability-guardrails/#6-incident-response)) |",
              "codeLang": "python",
              "code": "# src/main.py\nfrom fastapi import FastAPI, Request\nfrom fastapi.responses import StreamingResponse\nimport json, asyncio\n\napp = FastAPI()\n\n@app.post(\"/chat\")\nasync def chat(req: Request):\n    body = await req.json()\n    question = body[\"question\"]\n\n    async def event_stream():\n        try:\n            async for token in llm_stream(question):        # async generator\n                yield f\"data: {json.dumps({'token': token}, ensure_ascii=False)}\\n\\n\"\n                if await req.is_disconnected():             # client đóng tab -> dừng, khỏi tốn tiền\n                    break\n            yield \"data: [DONE]\\n\\n\"\n        except Exception as e:\n            yield f\"data: {json.dumps({'error': str(e)})}\\n\\n\"\n\n    return StreamingResponse(event_stream(), media_type=\"text/event-stream\")\n\n@app.get(\"/health\")\nasync def health():\n    return {\"status\": \"ok\"}",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-3-l4-t6",
              "title": "5. Hands-on: Dockerize Vietnamese LLM app + streaming FastAPI",
              "lead": "Dùng RAG app từ [Capstone Module I](https://handbook.yourclassacademy.com/llm-engineer/module-1/09-capstone/).",
              "concept": "Dùng RAG app từ [Capstone Module I](https://handbook.yourclassacademy.com/llm-engineer/module-1/09-capstone/).\n### Bước 1 - FastAPI streaming endpoint\n- `/chat` (POST) trả `StreamingResponse` SSE, có nhả `[DONE]`, dừng khi `req.is_disconnected()`.\n- `/health` cho healthcheck.\n- Client LLM async + `call_with_retry` (backoff + jitter).\n- `Semaphore(20)` giới hạn concurrency.\n### Bước 2 - Dockerfile\n- Multi-stage (build → runtime), non-root user, `HEALTHCHECK`.\n- `.dockerignore` loại `data/`, `.venv`, `*.gguf`, `.git`.\n- Vector index **không** nằm trong image - mount `-v ./data/index:/app/data/index:ro`.\n- Build, kiểm tra image size (mục tiêu \\< \\~400 MB cho app gọi API).\n### Bước 3 - Benchmark concurrency\n- Dùng `hey` / `wrk` / script `asyncio` bắn 50 request đồng thời vào `/chat`.\n- Đo: p50 / p95 latency, throughput (req/s), thời điểm bắt đầu xếp hàng do semaphore.\n- Thử `Semaphore(5)` vs `Semaphore(50)` → quan sát đánh đổi latency/throughput/lỗi 429.\n### Bước 4 (mở rộng) - Serve model local bằng vLLM\n- Nếu có GPU: chạy `vllm ... --model Qwen/Qwen2.5-7B-Instruct` trong container GPU.\n- Trỏ app vào `base_url=http://vllm:8000/v1` (docker-compose 2 service).\n- So throughput đồng thời giữa Ollama và vLLM trên cùng câu hỏi.\n### Tiêu chí hoàn thành\n- [ ] `/chat` stream token thật, dừng khi client ngắt kết nối\n- [ ] Image multi-stage, non-root, có healthcheck, không chứa weights/index\n- [ ] Retry có exponential backoff + jitter cho 429/timeout\n- [ ] Có số benchmark p50/p95/throughput ở ít nhất 2 mức concurrency\n- [ ] (Mở rộng) so sánh Ollama vs vLLM về throughput đồng thời",
              "codeLang": "text",
              "code": "",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-3-l4-t7",
              "title": "Tóm tắt",
              "lead": "| Chủ đề | Cốt lõi |",
              "concept": "| Chủ đề | Cốt lõi |\n| --- | --- |\n| Docker | Multi-stage; weights ngoài image; layer dependency trước code; non-root; healthcheck |\n| GPU image | Base `nvidia/cuda:*-runtime`, `--gpus all`, nvidia-container-toolkit; image rất nặng |\n| PagedAttention | KV cache như paging → tận dụng \\~96% bộ nhớ, nhiều seq đồng thời |\n| Continuous batching | Lập lịch mức iteration; request xong nhường slot ngay → GPU không idle |\n| Chọn stack | Ollama (dev) · vLLM/TGI (self-host, volume lớn) · API (mặc định để bắt đầu) |\n| FastAPI | SSE streaming; async client; semaphore backpressure; retry backoff + jitter; dừng khi disconnect |",
              "codeLang": "text",
              "code": "",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            }
          ]
        },
        {
          "id": "module-3-l5",
          "title": "Bài 5: Cloud Deployment (Compute Engine + Secret Manager)",
          "badge": "8 mục",
          "topics": [
            {
              "id": "module-3-l5-t1",
              "title": "Tổng quan",
              "lead": "Bài này đưa container từ Bài 4 lên một máy chủ cloud có public URL + HTTPS:",
              "concept": "Bài này đưa container từ Bài 4 lên một máy chủ cloud có **public URL + HTTPS**:\n- **Cloud landscape**: Compute Engine vs Cloud Run vs GKE vs Vertex AI - chọn theo trục nào.\n- Deploy trên **Compute Engine**: startup script, chạy container auto-restart.\n- **Production patterns**: nginx reverse proxy, HTTPS (Let's Encrypt), firewall, health check.\n- **Secrets**: vì sao `.env` trên server là nợ, và cách dùng **GCP Secret Manager**.",
              "codeLang": "text",
              "code": "",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-3-l5-t2",
              "title": "1. Cloud Landscape",
              "lead": "mermaid",
              "concept": "| Dịch vụ | Mô hình | Ưu | Nhược | Hợp với LLM app khi |\n| --- | --- | --- | --- | --- |\n| **Compute Engine** | VM, bạn quản OS | Toàn quyền, gắn GPU dễ, giá VM ổn định, chạy 24/7 rẻ | Tự lo OS patch, scaling, monitoring | Self-host vLLM (cần GPU), workload chạy liên tục, muốn 1 máy đơn giản |\n| **Cloud Run** | Container serverless, scale-to-zero | Không quản máy, tự scale theo request, trả theo dùng | Cold start; giới hạn thời gian request; GPU hạn chế | API stateless gọi provider ngoài, traffic thất thường, muốn ít vận hành |\n| **GKE** | Kubernetes managed | Orchestration mạnh, autoscale pod/node, GPU node pool | Phức tạp, cần biết K8s | Nhiều service (API + worker + vLLM), team có kinh nghiệm K8s |\n| **Vertex AI** | Nền tảng ML/LLM managed | Model Garden, endpoint có sẵn, tích hợp GCP | Khoá vào hệ sinh thái, giá endpoint cao | Muốn gọi Gemini/model open qua endpoint managed, có pipeline ML sẵn |\n> Module này dùng **Compute Engine + Secret Manager** làm mẫu vì nó minh hoạ trọn vẹn các production pattern (systemd, nginx, HTTPS, firewall) mà bạn phải hiểu dù sau này chuyển sang Cloud Run/GKE.",
              "codeLang": "mermaid",
              "code": "graph TD\n    Q{Đặc điểm workload?} --> GPU_Q[Cần GPU / chạy liên tục /<br/>kiểm soát OS]\n    Q --> STATELESS_Q[Stateless, traffic co giãn,<br/>chấp nhận cold start]\n    Q --> MULTI_Q[Nhiều service,<br/>cần orchestration]\n    Q --> MANAGED_Q[Muốn dùng model +<br/>endpoint có sẵn]\n    GPU_Q --> CE[Compute Engine]\n    STATELESS_Q --> CR[Cloud Run]\n    MULTI_Q --> GKE[GKE]\n    MANAGED_Q --> VX[Vertex AI]",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-3-l5-t3",
              "title": "2. Deploy trên Compute Engine",
              "lead": "bash",
              "concept": "- `--tags` để gắn firewall rule.\n- `--service-account` + `--scopes=cloud-platform`: cấp danh tính để VM đọc Secret Manager (mục 4). Không nhét key vào VM.\n### Startup script - cài Docker & chạy container khi máy khởi động\n\nLưu ý: container bind vào `127.0.0.1:8000` - **không** expose ra ngoài trực tiếp; nginx (mục 3) mới là thứ nghe 443.",
              "codeLang": "bash",
              "code": "gcloud compute instances create llm-app \\\n  --zone=asia-southeast1-a \\\n  --machine-type=e2-standard-2 \\\n  --boot-disk-size=30GB \\\n  --image-family=debian-12 --image-project=debian-cloud \\\n  --tags=http-server,https-server \\\n  --service-account=llm-app-sa@PROJECT.iam.gserviceaccount.com \\\n  --scopes=cloud-platform",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-3-l5-t4",
              "title": "3. Production Patterns",
              "lead": "mermaid",
              "concept": "### Auto-restart\n| Cách | Ghi chú |\n| --- | --- |\n| `systemd` unit với `Restart=always` (như mục 2) | Khuyến nghị - quản lý log, phụ thuộc, restart policy tập trung |\n| `docker run --restart=always` | Đơn giản hơn nhưng khó gắn health-based restart và log |\n| `docker compose` với `restart: always`  • `healthcheck` | Tốt khi có nhiều service (app + nginx + redis) |\n### nginx reverse proxy + HTTPS\n\n**SSE + nginx: phải tắt buffering**\nMặc định nginx buffer response → client không thấy token nào cho đến khi xong. Bắt buộc `proxy_buffering off;` và tăng `proxy_read_timeout` cho endpoint streaming.\n### Firewall\n\nPort 8000 của app **không** có rule → không thể truy cập từ ngoài, chỉ nginx ([localhost](http://localhost)) gọi được.\n### Health check\n- App expose `/health` (Bài 4).\n- nginx / uptime monitor gọi định kỳ.\n- Smoke test sau deploy (Bài 6) gọi `/health` + 1 câu hỏi thật.",
              "codeLang": "mermaid",
              "code": "graph LR\n    NET[Internet] -->|443| NGINX[nginx<br/>TLS termination + reverse proxy]\n    NGINX -->|127.0.0.1:8000| APP[Container llm-app<br/>systemd Restart=always]\n    FW[Firewall: chỉ mở 80/443] -.bảo vệ.- NGINX\n    CERT[certbot / Let's Encrypt<br/>auto-renew] -.cấp cert.-> NGINX",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-3-l5-t5",
              "title": "4. Secrets Management",
              "lead": "| Vấn đề của .env trên VM | Hệ quả |",
              "concept": "### Đọc secret lúc runtime (không nướng vào image/build)\n\n| Nguyên tắc | Vì sao |\n| --- | --- |\n| Đọc lúc **runtime** (khởi động app), không phải lúc `docker build` | Secret không nằm trong image layer |\n| VM dùng **Service Account + IAM**, không có key file trên máy | Không có gì để lộ qua backup |\n| Một secret = một resource, cấp quyền riêng | Phân quyền tối thiểu; audit theo secret |\n| Xoay vòng = `versions add`  • app đọc `latest` khi restart | Không cần SSH sửa file |\n| Local dev: dùng `.env` **không commit**  • `.env.example` | Chỉ production mới bắt buộc Secret Manager |\n**Cloud Run làm việc này gọn hơn**\nTrên Cloud Run bạn map secret vào biến môi trường hoặc file bằng cấu hình (`--set-secrets`), không cần code gọi API. Nguyên tắc không đổi: danh tính (service account) + IAM, đọc lúc chạy, không vào image.",
              "codeLang": "mermaid",
              "code": "graph LR\n    DEV[Người có quyền] -->|tạo / cập nhật version| SM[(Secret Manager<br/>OPENAI_API_KEY, DB_URL, ...)]\n    VM[Compute Engine VM] -->|Service Account + IAM<br/>secretmanager.secretAccessor| SM\n    SM -->|đọc lúc runtime| APP[App: nạp vào env / config trong bộ nhớ]",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-3-l5-t6",
              "title": "5. Vận hành cơ bản",
              "lead": "| Việc | Cách |",
              "concept": "| Việc | Cách |\n| --- | --- |\n| **Xem log** | `journalctl -u llm-app -f` (systemd) hoặc `docker logs -f llm-app`; đẩy lên Cloud Logging bằng logging agent |\n| **Log rotation** | Docker `--log-opt max-size=10m --log-opt max-file=3`; hoặc `logrotate` cho nginx |\n| **Restart an toàn** | `systemctl restart llm-app`; với nhiều instance sau LB: rolling (drain 1 máy → restart → chờ health → máy kế) |\n| **Backup vector index** | `gsutil rsync /data/index gs://backup/index/$(date +%F)` theo cron; hoặc snapshot disk |\n| **Cập nhật app** | Đẩy image tag mới → `docker pull`  • `systemctl restart` (tự động hoá ở Bài 6) |",
              "codeLang": "text",
              "code": "",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-3-l5-t7",
              "title": "6. Hands-on: Deploy Vietnamese RAG chatbot có public URL",
              "lead": "Dùng image từ Bài 4 (RAG chatbot Capstone Module I).",
              "concept": "Dùng image từ Bài 4 (RAG chatbot Capstone Module I).\n### Bước 1 - Chuẩn bị secret\n- `gcloud secrets create OPENAI_API_KEY` (và `EMBEDDING_API_KEY` nếu tách).\n- Tạo service account `llm-app-sa`, cấp `roles/secretmanager.secretAccessor` cho từng secret.\n- Sửa `src/config.py` đọc secret qua Secret Manager; local vẫn fallback `.env`.\n### Bước 2 - Tạo VM + startup script\n- `gcloud compute instances create` với `--tags=https-server`, gắn service account.\n- Startup script: cài Docker, `docker pull`, tạo `llm-app.service` (`Restart=always`, bind `127.0.0.1:8000`).\n- Copy/tải vector index vào `/data/index` trên VM (scp hoặc `gsutil cp`).\n### Bước 3 - nginx + HTTPS\n- Trỏ 1 subdomain (hoặc dùng DNS tạm / `nip.io`) về IP tĩnh của VM.\n- Cài nginx, cấu hình reverse proxy `127.0.0.1:8000`, **`proxy_buffering off`** cho `/chat`.\n- `certbot --nginx -d <domain>` cấp cert; xác nhận `certbot.timer` chạy.\n### Bước 4 - Firewall + verify\n- Firewall: mở 80/443 cho `0.0.0.0/0`, SSH giới hạn IP của bạn.\n- Xác nhận port 8000 **không** truy cập được từ ngoài (`curl http://<IP>:8000` timeout).\n- `curl https://<domain>/health` → ok; hỏi 1 câu qua UI → thấy token stream dần.\n### Bước 5 - Vận hành thử\n- `journalctl -u llm-app -f`, thử `kill` container → systemd tự dựng lại trong \\~5s.\n- Xoay `OPENAI_API_KEY` (`versions add`) → `systemctl restart llm-app` → app dùng key mới.\n- Script backup `/data/index` lên GCS.\n### Tiêu chí hoàn thành\n- [ ] Public URL `https://...` trả lời được, cert hợp lệ, tự renew\n- [ ] Không có API key nào nằm trên VM dưới dạng file / trong image\n- [ ] Port app (8000) không truy cập được từ Internet\n- [ ] `/chat` stream token qua nginx (buffering đã tắt)\n- [ ] Kill container → tự restart; xoay secret → chỉ cần restart, không sửa file",
              "codeLang": "text",
              "code": "",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-3-l5-t8",
              "title": "Tóm tắt",
              "lead": "mermaid",
              "concept": "| Chủ đề | Cốt lõi |\n| --- | --- |\n| Cloud landscape | CE (GPU, chạy liên tục) · Cloud Run (stateless, scale-to-zero) · GKE (nhiều service) · Vertex (managed model) |\n| Compute Engine deploy | Startup script + systemd `Restart=always`; container bind [localhost](http://localhost), không expose |\n| nginx + HTTPS | TLS termination, reverse proxy; `proxy_buffering off` cho SSE; certbot auto-renew |\n| Firewall | Chỉ mở 80/443; port app không có rule → private |\n| Secrets | `.env` trên server = nợ; Secret Manager + Service Account + IAM; đọc lúc runtime, không vào image |\n| Vận hành | `journalctl`/`docker logs`, log rotation, rolling restart, backup index |",
              "codeLang": "mermaid",
              "code": "graph LR\n    IMG[(Image trong Artifact Registry)] --> VM[Compute Engine VM<br/>Service Account, tags firewall]\n    VM --> SYSD[systemd: container Restart=always, bind 127.0.0.1:8000]\n    NGINX[nginx :443<br/>TLS + proxy, buffering off] --> SYSD\n    LE[Let's Encrypt auto-renew] --> NGINX\n    FW[Firewall: chỉ 80/443 + SSH hạn chế] --> NGINX\n    SM[(Secret Manager)] -->|IAM secretAccessor| SYSD",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            }
          ]
        },
        {
          "id": "module-3-l6",
          "title": "Bài 6: CI/CD for LLM Apps",
          "badge": "8 mục",
          "topics": [
            {
              "id": "module-3-l6-t1",
              "title": "Tổng quan",
              "lead": "CI/CD cho LLM app không có bước retrain, nhưng có hai thứ mà pipeline phần mềm thông thường thiếu: prompt testing và eval gate. Bài này dựng workflow GitHub Actions:",
              "concept": "CI/CD cho LLM app không có bước retrain, nhưng có hai thứ mà pipeline phần mềm thông thường thiếu: **prompt testing** và **eval gate**. Bài này dựng workflow GitHub Actions:\n- **CI**: prompt linting + unit test tool/chain + eval gate (gọi pipeline từ [Bài 2](https://handbook.yourclassacademy.com/llm-engineer/module-3/02-eval-pipelines/)) chặn merge khi chất lượng tụt.\n- **CD**: build image → push → deploy lên môi trường từ [Bài 5](https://handbook.yourclassacademy.com/llm-engineer/module-3/05-cloud-deploy/) → smoke test → rollback được.",
              "codeLang": "text",
              "code": "",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-3-l6-t2",
              "title": "1. CI/CD cho LLM App khác gì",
              "lead": "mermaid",
              "concept": "| Thứ đáng chặn merge | Kiểm bằng |\n| --- | --- |\n| Prompt thiếu biến / sai cú pháp / version không hợp lệ | Prompt lint (mục 4) |\n| Tool trả sai schema, chain vỡ | Unit test |\n| Eval score tụt quá tolerance ở tổng hoặc slice quan trọng | Eval gate |\n| Cost/latency trung bình tăng bất thường | Guardrail metric trong eval report |",
              "codeLang": "mermaid",
              "code": "graph LR\n    subgraph \"App thường\"\n        C1[Code] --> U1[Unit / integration test] --> B1[Build] --> D1[Deploy] --> S1[Smoke test]\n    end\n    subgraph \"LLM app - thêm 2 khối\"\n        C2[Code + Prompt + Eval set] --> L2[Prompt lint] --> U2[Unit test tool/chain]\n        U2 --> E2[Eval gate - điểm không được tụt] --> B2[Build] --> D2[Deploy] --> S2[Smoke test thật]\n    end",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-3-l6-t3",
              "title": "2. Góc nhìn ML để so sánh",
              "lead": "Để hiểu vì sao LLM CI/CD nhẹ hơn MLOps ở một số mặt:",
              "concept": "Để hiểu vì sao LLM CI/CD nhẹ hơn MLOps ở một số mặt:\n| Khía cạnh MLOps | LLM app tương ứng |\n| --- | --- |\n| Data validation (schema, phân bố, thiếu giá trị) | Validate golden set (case có đủ trường, slice hợp lệ); validate tài liệu nguồn trước khi ingest |\n| Model validation (so metric với baseline trước khi promote) | Eval gate - so eval score với baseline |\n| Training dài, tốn GPU | Không có (trừ nhánh fine-tuning phụ) → CI chạy trên runner thường, tính bằng phút |\n| Continuous Training (CT): tự retrain khi data drift | Thường không cần – cải tiến = sửa prompt/RAG/eval, không phải weights |\n| Model registry (weights + metadata) | Prompt registry ([Bài 1](https://handbook.yourclassacademy.com/llm-engineer/module-3/01-llmops-prompt-mgmt/)) - prompt version + eval_score |\nChỉ khi bạn thật sự fine-tune (LoRA từ [M1, Bài 3](https://handbook.yourclassacademy.com/llm-engineer/module-1/03-finetuning/)). Lúc đó thêm một pipeline tách biệt: `validate data → train → eval → register model`, chạy thủ công hoặc theo lịch, không nằm trên đường CI của mỗi PR.",
              "codeLang": "text",
              "code": "",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-3-l6-t4",
              "title": "3. GitHub Actions Nền Tảng",
              "lead": "| Khái niệm | Vai trò |",
              "concept": "| Khái niệm | Vai trò |\n| --- | --- |\n| **Workflow** | Một quy trình tự động |\n| **Trigger** | `pull_request`, `push`, `schedule`, `workflow_dispatch` |\n| **Job** | Nhóm step chạy trên một runner |\n| **Runner** | Máy chạy job - `ubuntu-latest` hoặc self-hosted |\n| **Secrets** | `${{ secrets.OPENAI_API_KEY }}` |\n| **Cache** | Cache `~/.cache/pip`, `.eval_cache` |\n| **Environment** | `production` với protection rule |",
              "codeLang": "yaml",
              "code": "name: ci\non:\n  pull_request:\n    branches: [main]\nconcurrency:\n  group: ci-${{ github.ref }}\n  cancel-in-progress: true\njobs:\n  lint-and-test:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n      - uses: actions/setup-python@v5\n        with: { python-version: \"3.12\" }\n      - uses: actions/cache@v4\n        with:\n          path: ~/.cache/pip\n          key: pip-${{ hashFiles('requirements.txt') }}\n      - run: pip install -r requirements.txt -r requirements-dev.txt\n      - run: python -m prompts.lint prompts/\n      - run: ruff check . && ruff format --check .\n      - run: pytest tests/unit -q",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-3-l6-t5",
              "title": "4. CI Patterns cho LLM",
              "lead": "python",
              "concept": "Lint bắt: thiếu metadata, version sai kiểu, template quá dài, biến dùng mà chưa khai báo (lỗi phổ biến nhất - xem [Bài 1](https://handbook.yourclassacademy.com/llm-engineer/module-3/01-llmops-prompt-mgmt/#3-prompt-versioning-templates)).\n### Unit test tool & chain\n\nĐây là test deterministic - không gọi LLM thật (mock), chạy nhanh, luôn bật.\n### Eval gate trên PR\n\nBật branch protection: require check `eval-gate / eval` pass trước khi merge vào `main`.\n### Kiểm soát chi phí CI\n| Kỹ thuật | Chi tiết |\n| --- | --- |\n| Subset thay full | 20–40 case trên PR; full 100–300 chạy nightly |\n| Cache LLM response | Key `(rendered_prompt, model, params)` |\n| Judge model rẻ trên PR | `gpt-4o-mini` cho subset; model mạnh cho nightly |\n| `paths:` filter | Bỏ eval nếu PR chỉ đụng docs/CSS |\n| `concurrency: cancel-in-progress` | Push liên tục huỷ run cũ |",
              "codeLang": "python",
              "code": "# prompts/lint.py\nimport sys, glob, yaml\nfrom string import Template\n\nREQUIRED_META = {\"name\", \"version\", \"model\", \"owner\", \"changelog\"}\nMAX_TEMPLATE_CHARS = 12000\n\ndef lint_file(path: str) -> list[str]:\n    errs = []\n    doc = yaml.safe_load(open(path, encoding=\"utf-8\"))\n    missing = REQUIRED_META - doc.keys()\n    if missing:\n        errs.append(f\"{path}: thiếu metadata {missing}\")\n    if not isinstance(doc.get(\"version\"), int) or doc[\"version\"] < 1:\n        errs.append(f\"{path}: version phải là số nguyên >= 1\")\n    tpl = doc.get(\"template\", \"\")\n    if len(tpl) > MAX_TEMPLATE_CHARS:\n        errs.append(f\"{path}: template quá dài ({len(tpl)} ký tự)\")\n    declared = set(doc.get(\"variables\", []))\n    used = {m for m in Template(tpl).get_identifiers()} if hasattr(Template, \"get_identifiers\") else set()\n    if used - declared:\n        errs.append(f\"{path}: biến dùng nhưng chưa khai báo: {used - declared}\")\n    return errs\n\nif __name__ == \"__main__\":\n    all_errs = [e for f in glob.glob(f\"{sys.argv[1]}/**/*.yaml\", recursive=True) for e in lint_file(f)]\n    for e in all_errs:\n        print(\"::error::\" + e)\n    sys.exit(1 if all_errs else 0)",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-3-l6-t6",
              "title": "5. CD Patterns",
              "lead": "mermaid",
              "concept": "### Workflow CD",
              "codeLang": "mermaid",
              "code": "graph LR\n    MERGE[Merge vào main] --> BUILD[Build image + tag = git SHA]\n    BUILD --> PUSH[Push -> Artifact Registry]\n    PUSH --> DEPLOY[Deploy: VM pull tag mới + restart]\n    DEPLOY --> SMOKE[Smoke test: /health + 2 câu hỏi thật]\n    SMOKE -->|pass| DONE[Xong - lưu tag là last-known-good]\n    SMOKE -->|fail| RB[Rollback: pull last-known-good + restart]",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-3-l6-t7",
              "title": "6. Hands-on: Workflow eval gate chặn deploy",
              "lead": "- prompts/lint.py + step gọi nó trong ci.yml.",
              "concept": "",
              "codeLang": "text",
              "code": "",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-3-l6-t8",
              "title": "Tóm tắt",
              "lead": "mermaid",
              "concept": "| Chủ đề | Cốt lõi |\n| --- | --- |\n| Khác MLOps | Không retrain; CI chạy phút; thêm prompt lint + eval gate |\n| GitHub Actions | trigger · job/needs · runner · secrets · cache · environment |\n| Prompt lint | Metadata đủ, version đúng kiểu, biến khai báo khớp |\n| Eval gate | Subset trên PR + branch protection; cache response |\n| CD | Tag = git SHA; deploy → smoke test → rollback tự động |\n| Rollback | 3 trục: image tag · prompt version alias · model config |",
              "codeLang": "mermaid",
              "code": "graph LR\n    PR[Pull Request] --> LINT[Prompt lint + ruff]\n    LINT --> UT[Unit test tool/chain - mock LLM]\n    UT --> EG{Eval gate<br/>subset, so baseline}\n    EG -->|tụt| BLOCK[Chặn merge + comment report]\n    EG -->|ổn| MERGE[Merge main]\n    MERGE --> CD[Build tag=SHA -> push -> deploy -> smoke]\n    CD -->|smoke pass| LKG[Ghi last-known-good]\n    CD -->|smoke fail| RB[Rollback image / prompt / model]",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            }
          ]
        },
        {
          "id": "module-3-l7",
          "title": "Bài 7: LLM Observability & Guardrails at Scale",
          "badge": "9 mục",
          "topics": [
            {
              "id": "module-3-l7-t1",
              "title": "Tổng quan",
              "lead": "[Module I, Bài 7](https://handbook.yourclassacademy.com/llm-engineer/module-1/07-evaluation-guardrails/) dạy guardrails cơ bản (prompt injection, PII, output validation) và setup LangSmith/LangFuse. [Module II, Bài 5](https://handbook.yourc",
              "concept": "[Module I, Bài 7](https://handbook.yourclassacademy.com/llm-engineer/module-1/07-evaluation-guardrails/) dạy guardrails cơ bản (prompt injection, PII, output validation) và setup LangSmith/LangFuse. [Module II, Bài 5](https://handbook.yourclassacademy.com/llm-engineer/module-2/05-agent-eval/) dạy tracing agent và OpenTelemetry. Bài này chuyển sang \"vận hành ở scale\":\n- Ba tầng observability và câu hỏi mỗi tầng trả lời.\n- Tracing production: sampling, PII trong trace, chi phí của chính observability.\n- Production dashboard: cost per feature, hallucination rate, user feedback, SLO.\n- Guardrails ở scale: latency overhead, false positive, fail-open vs fail-closed.\n- Incident response: 4 playbook (cost spike, hallucination spike, jailbreak, provider outage).",
              "codeLang": "text",
              "code": "",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-3-l7-t2",
              "title": "1. Ba tầng observability",
              "lead": "mermaid",
              "concept": "| Tầng | Trả lời câu hỏi | Ví dụ công cụ |\n| --- | --- | --- |\n| **Trace** | \"Request này chậm/sai ở bước nào?\" | LangSmith, LangFuse, OTel + Jaeger |\n| **Metric** | \"Xu hướng cost/latency/chất lượng đang đi đâu?\" | Prometheus/Grafana, Cloud Monitoring, dashboard của LangSmith |\n| **Log** | \"Chuyện gì xảy ra lúc 02:14? Có bao nhiêu lần fallback?\" | Cloud Logging, Loki, ELK |\n> **Quy tắc:** trace để debug một ca, metric để phát hiện xu hướng, log để điều tra sự kiện. Thiếu tầng nào là mù ở loại câu hỏi đó.",
              "codeLang": "mermaid",
              "code": "graph TB\n    T[Trace<br/>1 request: mọi node, tool call, token, latency] --> M[Metric<br/>tổng hợp theo thời gian: cost, p95, hit rate]\n    M --> L[Log<br/>sự kiện rời rạc: lỗi, guardrail trigger, fallback]",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-3-l7-t3",
              "title": "2. Tracing Production",
              "lead": "Ở volume cao, lưu mọi trace tốn tiền và chậm. Chiến lược:",
              "concept": "",
              "codeLang": "python",
              "code": "def should_sample(ctx) -> bool:\n    if ctx.error or ctx.latency_ms > P99 or ctx.guardrail_triggered:\n        return True                     # tail: giữ ca bất thường\n    return random.random() < 0.05       # head: 5% ca bình thường",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-3-l7-t4",
              "title": "3. Token & Cost Analytics",
              "lead": "Dùng lại recordcost() từ [Bài 3](https://handbook.yourclassacademy.com/llm-engineer/module-3/03-cost-caching/#2-o-truoc-khi-toi-uu), gắn tag đủ để cắt lát:",
              "concept": "Dùng lại `record_cost()` từ [Bài 3](https://handbook.yourclassacademy.com/llm-engineer/module-3/03-cost-caching/#2-o-truoc-khi-toi-uu), gắn tag đủ để cắt lát:\n\nTrace phải tách được các span này. Thường phát hiện: rerank hoặc guardrail âm thầm cộng 200–400ms; hoặc retrieval chậm khi index lớn lên.",
              "codeLang": "python",
              "code": "metrics.emit(\"llm_cost_usd\", cost, tags={\n    \"feature\": feature,        # rag_answer, summarize, classify...\n    \"model\": model,\n    \"cache\": \"hit\" | \"miss\",\n    \"cascade\": \"cheap\" | \"escalated\",\n    \"prompt_version\": pv,\n})",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-3-l7-t5",
              "title": "4. Production Dashboard",
              "lead": "mermaid",
              "concept": "| Widget | Nguồn dữ liệu | Ngưỡng cảnh báo gợi ý |\n| --- | --- | --- |\n| **Cost per feature** | `llm_cost_usd` tag `feature` | Feature tăng \\> 50% tuần-trên-tuần; tổng \\> 120% dự phóng |\n| **Hallucination rate** | Judge/RAGAS faithfulness trên mẫu 1–5% traffic | Faithfulness \\< baseline − 0.05 |\n| **Latency p95** | Span tổng | p95 \\> SLO (ví dụ 4s); p99 \\> 2× p95 |\n| **User feedback** | Nút thumbs; tín hiệu ngầm: bỏ giữa chừng, hỏi lại ngay, copy đáp án | Tỉ lệ thumbs-down \\> X%; retry-rate tăng |\n| **Error / fallback** | Log tag loại (429, timeout, guardrail block, provider fallback) | Bất kỳ loại nào tăng đột biến |\n| **SLO / error budget** | availability + latency SLO | Error budget cháy nhanh hơn dự kiến |\n### Tín hiệu ngầm từ người dùng\nKhông phải ai cũng bấm thumbs. Tín hiệu rẻ mà giá trị:\n- **Regenerate / hỏi lại ngay** trong \\< 10s → câu trả lời có thể tệ.\n- **Bỏ giữa stream** → quá chậm hoặc lạc đề.\n- **Copy đoạn trả lời** → có thể hữu ích.\n- **Rời phiên ngay sau 1 câu** → không giải quyết được nhu cầu.",
              "codeLang": "mermaid",
              "code": "graph TB\n    subgraph \"Dashboard production\"\n        A[Cost per feature<br/>ngày / tuần]\n        B[Faithfulness / hallucination rate<br/>chấm judge trên mẫu]\n        C[Latency p50 / p95 / p99<br/>tổng + theo span]\n        D[User feedback<br/>thumbs + tín hiệu ngầm]\n        E[Cache hit rate<br/>tầng 1 + tầng 2]\n        F[Error rate + fallback count<br/>theo loại]\n        G[SLO / error budget<br/>còn lại bao nhiêu]\n    end",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-3-l7-t6",
              "title": "5. Guardrails at Scale",
              "lead": "Guardrails cơ bản đã có ở [M1, Bài 7](https://handbook.yourclassacademy.com/llm-engineer/module-1/07-evaluation-guardrails/#3-guardrails). Ở production, câu hỏi chuyển từ \"làm thế nào\" sang \"chịu được chi phí vận hành không\".",
              "concept": "Guardrails cơ bản đã có ở [M1, Bài 7](https://handbook.yourclassacademy.com/llm-engineer/module-1/07-evaluation-guardrails/#3-guardrails). Ở production, câu hỏi chuyển từ \"làm thế nào\" sang **\"chịu được chi phí vận hành không\"**.\n\n| Vấn đề vận hành | Chi tiết |\n| --- | --- |\n| **Latency overhead** | Mỗi guard là thêm 50–300ms (regex rẻ; LLM-based detector đắt). Đo và ngân sách hoá; chạy song song các guard độc lập |\n| **False positive rate** | Guard quá gắt chặn cả câu hợp lệ → user bực. Đo FP trên traffic thật; tune ngưỡng; log mọi lần block để review |\n| **Fail-open vs fail-closed** | Guard service lỗi/timeout thì làm gì? |\n| **Thứ tự & chi phí** | Chạy guard rẻ trước (regex PII) rồi mới guard đắt (LLM injection detector); dừng sớm khi đã block |\n### Fail-open vs Fail-closed\n|  | Fail-open (cho qua khi guard lỗi) | Fail-closed (chặn khi guard lỗi) |\n| --- | --- | --- |\n| Rủi ro | Nội dung xấu lọt khi guard down | Từ chối cả request hợp lệ khi guard down |\n| Hợp với | Guard \"nice-to-have\" (ví dụ format check) | Guard bắt buộc (PII leak, nội dung nguy hiểm) |\n| Bắt buộc kèm | Alert khi rơi vào fail-open + đếm số lần | Fallback nhẹ hơn (regex-only) trước khi từ chối hẳn |\nGuardrail cũng là điểm lỗi. Một LLM-based injection detector gọi model ngoài: nó timeout thì cả request treo. Đặt timeout riêng, có nhánh fallback (regex), và log mỗi lần fallback → đưa lên dashboard (mục 4, \"Error / fallback\").",
              "codeLang": "mermaid",
              "code": "graph LR\n    IN[Input] --> GI[Input guard<br/>injection, PII, off-topic]\n    GI -->|pass| LLM[LLM]\n    GI -->|block| REFUSE1[Từ chối / hỏi lại]\n    LLM --> GO[Output guard<br/>PII leak, groundedness, toxicity, format]\n    GO -->|pass| OUT[Trả người dùng]\n    GO -->|fail| ACT{Fail-open / Fail-closed?}",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-3-l7-t7",
              "title": "6. Incident Response",
              "lead": "Bốn playbook. Mỗi playbook: tín hiệu phát hiện → khoanh vùng → giảm thiểu → sau sự cố.",
              "concept": "Bốn playbook. Mỗi playbook: **tín hiệu phát hiện → khoanh vùng → giảm thiểu → sau sự cố**.\n### 6.1. Cost Spike\n| Bước | Hành động |\n| --- | --- |\n| Phát hiện | Alert budget ([Bài 3](https://handbook.yourclassacademy.com/llm-engineer/module-3/03-cost-caching/#7-cost-governance)): chi phí giờ này \\> 3× trung bình; hoặc đạt 80% ngân sách sớm bất thường |\n| Khoanh vùng | Dashboard cost per feature + per user: feature nào / user nào nhảy vọt? Cache hit rate có tụt (key bị đổi)? Prompt version mới có làm context phình? |\n| Giảm thiểu | Bật/giảm ngưỡng hard limit per user; tạm route feature thủ phạm sang model rẻ; nếu do cache miss hàng loạt → rollback thay đổi làm hỏng cache key; nếu do loop agent → giảm `max_iterations` |\n| Sau sự cố | Thêm alert sớm hơn; thêm test cache-key vào CI; ghi runbook |\n### 6.2. Hallucination Spike\n| Bước | Hành động |\n| --- | --- |\n| Phát hiện | Faithfulness (judge trên mẫu) tụt dưới baseline − 0.05; thumbs-down tăng; feedback \"sai thông tin\" |\n| Khoanh vùng | Đổi gì gần đây: prompt version? model? retrieval (index rebuild, embedding đổi)? Slice nào tệ nhất (dùng eval theo slice [Bài 2](https://handbook.yourclassacademy.com/llm-engineer/module-3/02-eval-pipelines/#5-regression-testing))? |\n| Giảm thiểu | Rollback prompt version / model config về last-known-good ([Bài 6](https://handbook.yourclassacademy.com/llm-engineer/module-3/06-cicd/#5-cd-patterns)); nếu do index → khôi phục snapshot index trước đó; siết guardrail groundedness tạm thời |\n| Sau sự cố | Thêm case vào golden set từ đúng các câu bị sai; siết eval gate cho slice liên quan |\n### 6.3. Jailbreak / Prompt Injection Attempt\n| Bước | Hành động |\n| --- | --- |\n| Phát hiện | Guardrail injection log tăng đột biến; xuất hiện output rò rỉ system prompt / phá vai; một user gửi nhiều biến thể tấn công |\n| Khoanh vùng | Mẫu tấn công nào đang lọt? Từ ít user hay lan rộng? Guard đang fail-open? |\n| Giảm thiểu | Chuyển guard injection sang fail-closed cho traffic nghi ngờ; thêm pattern vào input filter; rate-limit / block user tấn công; nếu system prompt bị lộ → xoay các secret nhắc trong đó |\n| Sau sự cố | Thêm mẫu tấn công vào golden set slice `injection`; red-team lại; xem [M1, Bài 7](https://handbook.yourclassacademy.com/llm-engineer/module-1/07-evaluation-guardrails/#prompt-injection-defense) |\n### 6.4. Provider Outage / Degradation\n| Bước | Hành động |\n| --- | --- |\n| Phát hiện | Error rate `5xx` / timeout từ provider tăng; latency p95 tăng gấp bội; status page provider |\n| Khoanh vùng | Một model hay cả provider? Khu vực nào? Có phải quota bị vượt (429 chứ không phải 5xx)? |\n| Giảm thiểu | Chuyển sang **fallback model/provider** đã cấu hình sẵn; bật retry backoff dài hơn ([Bài 4](https://handbook.yourclassacademy.com/llm-engineer/module-3/04-containerisation-serving/#4-fastapi-patterns-cho-llm)); giảm tính năng không thiết yếu; hiện banner \"đang chậm\" |\n| Sau sự cố | Kiểm tra fallback có thực sự chạy (diễn tập định kỳ); điều chỉnh timeout/retry; đa dạng hoá provider cho tính năng quan trọng |",
              "codeLang": "python",
              "code": "# Fallback provider - cấu hình sẵn, diễn tập định kỳ\nPROVIDERS = [\"claude-sonnet-5\", \"gpt-4o\"]     # thứ tự ưu tiên\n\nasync def generate(messages) -> str:\n    last = None\n    for model in PROVIDERS:\n        try:\n            return await call_with_retry(model=model, messages=messages)\n        except (ProviderError, APITimeoutError) as e:\n            last = e\n            metrics.emit(\"provider_fallback\", 1, tags={\"from\": model})\n    raise last",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-3-l7-t8",
              "title": "7. Hands-on: LangSmith tracing + cost dashboard cho Vietnamese RAG agent",
              "lead": "Dùng RAG agent từ [Capstone Module I](https://handbook.yourclassacademy.com/llm-engineer/module-1/09-capstone/) đã deploy ở [Bài 5](https://handbook.yourclassacademy.com/llm-engineer/module-3/05-cloud-deploy/).",
              "concept": "Dùng RAG agent từ [Capstone Module I](https://handbook.yourclassacademy.com/llm-engineer/module-1/09-capstone/) đã deploy ở [Bài 5](https://handbook.yourclassacademy.com/llm-engineer/module-3/05-cloud-deploy/).\n### Bước 1 - Tracing có sampling\n- Bật LangSmith/LangFuse tracing (như [M1, Bài 7](https://handbook.yourclassacademy.com/llm-engineer/module-1/07-evaluation-guardrails/#4-monitoring-voi-langsmith-langfuse)).\n- Thêm `should_sample()`: 100% ca lỗi/guardrail/slow, 5% ca bình thường.\n- Redact PII ở hook trước export (regex tiếng Việt cho SĐT, email, CCCD).\n- Đặt retention 30 ngày cho trace.\n### Bước 2 - Span breakdown\n- Instrument các span: `query_rewrite`, `retrieve`, `rerank`, `llm_generate`, `output_guard`.\n- Chạy 30 câu hỏi, xem trace: span nào chiếm nhiều thời gian nhất?\n### Bước 3 - Cost dashboard\n- `record_cost()` với tag `feature`, `model`, `cache`, `prompt_version`.\n- Dashboard (Grafana/Cloud Monitoring/LangSmith) với widget: cost per feature (ngày), latency p50/p95/p99, cache hit rate, error/fallback count.\n- Chấm faithfulness bằng judge trên 5% traffic → widget hallucination rate.\n### Bước 4 - Alert + một incident\n- Alert: cost giờ này \\> 3× trung bình 7 ngày → gửi Slack/email.\n- Diễn tập **cost spike**: tạm sửa prompt cho context phình gấp 3 (lấy top-30 chunk) → chạy tải → xác nhận alert kêu → theo playbook 6.1 khoanh vùng bằng dashboard → rollback prompt version.\n### Bước 5 (mở rộng) - Fallback provider\n- Cấu hình `PROVIDERS` với 2 model khác nhà.\n- Giả lập outage (chặn network tới provider 1 / trả 503) → xác nhận tự chuyển provider 2, `provider_fallback` metric tăng, người dùng vẫn có câu trả lời.\n### Tiêu chí hoàn thành\n- [ ] Trace có sampling (100% ca bất thường, \\~5% ca thường) + PII đã redact\n- [ ] Trace tách được span; chỉ ra được bước chậm nhất\n- [ ] Dashboard có ≥ 5 widget: cost/feature, latency p95, cache hit, error/fallback, hallucination rate\n- [ ] Alert cost spike hoạt động (đã kích hoạt thật trong diễn tập)\n- [ ] Thực hiện trọn 1 playbook incident: phát hiện → khoanh vùng bằng dashboard → mitigate\n- [ ] (Mở rộng) fallback provider chạy khi provider chính lỗi",
              "codeLang": "text",
              "code": "",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-3-l7-t9",
              "title": "Tóm tắt",
              "lead": "mermaid",
              "concept": "| Chủ đề | Cốt lõi |\n| --- | --- |\n| Ba tầng | Trace (debug 1 ca) · Metric (xu hướng) · Log (điều tra sự kiện) |\n| Tracing prod | Head/tail sampling; redact PII trước export; retention ngắn cho nội dung; ngân sách hoá chi phí observability |\n| Dashboard | Cost/feature, faithfulness (judge trên mẫu), latency p95/p99, feedback + tín hiệu ngầm, error/fallback, SLO |\n| Guardrails at scale | Đo latency overhead + false positive; guard rẻ trước; fail-open vs fail-closed có chủ đích; guard cũng là điểm lỗi |\n| Incident response | 4 playbook chung khung: phát hiện → khoanh vùng → giảm thiểu → sau sự cố; fallback phải được diễn tập |",
              "codeLang": "mermaid",
              "code": "graph LR\n    APP[RAG / Agent] --> TRACE[Trace có sampling + redact PII]\n    APP --> METRIC[Metric: cost/feature, p95, hit rate, hallucination]\n    APP --> LOG[Log: lỗi, guardrail, fallback]\n    METRIC --> DASH[Dashboard + SLO]\n    DASH --> ALERT{Alert}\n    ALERT -->|cost spike| P1[Playbook: khoanh feature/user -> hard limit / route rẻ / rollback]\n    ALERT -->|hallucination| P2[Playbook: rollback prompt/model/index + thêm golden case]\n    ALERT -->|jailbreak| P3[Playbook: fail-closed + block user + thêm injection case]\n    ALERT -->|provider outage| P4[Playbook: fallback provider + retry dài + giảm tính năng]",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            }
          ]
        },
        {
          "id": "module-3-l8",
          "title": "Bài 8: Capstone - Production LLM System",
          "badge": "8 mục",
          "topics": [
            {
              "id": "module-3-l8-t1",
              "title": "Tổng quan",
              "lead": "Capstone tích hợp toàn bộ Module III thành một pipeline production hoàn chỉnh cho hệ thống LLM đã xây ở Module I/II:",
              "concept": "Capstone tích hợp toàn bộ Module III thành **một pipeline production hoàn chỉnh** cho hệ thống LLM đã xây ở Module I/II:\n- Prompt được version hoá trong registry (Bài 1).\n- Mọi thay đổi đi qua **eval gate** (Bài 2).\n- **CI/CD** tự động lint → eval → build → deploy → smoke test → rollback (Bài 6).\n- Deploy trên Compute Engine + Secret Manager (Bài 5), container hoá chuẩn (Bài 4).\n- Cache 2 tầng + cost governance (Bài 3).\n- **Observability + guardrails + incident playbook** (Bài 7).\n- Có **vòng feedback**: log production → case mới trong golden set.\nĐịnh dạng buổi học\nLive coding (architecture review & integration) + học viên hoàn thiện pipeline trên hệ thống của mình + phần take-home + Q&A.",
              "codeLang": "text",
              "code": "",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-3-l8-t2",
              "title": "1. Kiến trúc pipeline",
              "lead": "mermaid",
              "concept": "### Vì sao không có bước \"train\" trong đường chính\nHệ thống LLM ở Module I/II cải tiến qua **prompt, RAG, eval** - không qua cập nhật weights. Pipeline chính là:\n> `prompt/dataset version → evaluate → register → deploy → monitor → (feedback về golden set)`\nNếu dự án có fine-tuning\nĐưa LoRA (M1, Bài 3) vào như **nhánh phụ tách biệt**: `validate data → train → eval → register model`, chạy thủ công/theo lịch, kết quả là một `model config` mới mà pipeline chính ở trên tiêu thụ (và vẫn phải qua eval gate).",
              "codeLang": "mermaid",
              "code": "graph LR\n    DEV[\"Sửa prompt / code / config\"] --> PR[\"Pull Request\"]\n    PR --> LINT[\"Prompt lint + unit test\"]\n    LINT --> EVAL{\"Eval gate<br>subset, so baseline + slice\"}\n    EVAL -->|fail| DEV\n    EVAL -->|pass| MERGE[\"Merge main\"]\n    MERGE --> REG[\"Promote prompt version -> alias production\"]\n    MERGE --> BUILD[\"Build image tag=SHA -> Artifact Registry\"]\n    BUILD --> DEPLOY[\"Deploy: VM pull + systemd restart\"]\n    DEPLOY --> SMOKE[\"Smoke test: /health + câu hỏi thật\"]\n    SMOKE -->|fail| RB[\"Rollback: image tag / prompt alias / model config\"]\n    SMOKE -->|pass| PROD[\"Production<br>cache 2 tầng + guardrails\"]\n    PROD --> OBS[\"Observability: trace sampled + cost dashboard + alert\"]\n    OBS -->|case sai / feedback âm| GOLDEN[(\"Golden Set +1 case\")]\n    GOLDEN --> EVAL\n    OBS -->|cost / hallucination / jailbreak / outage| PLAYBOOK[\"Incident playbook\"]",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-3-l8-t3",
              "title": "2. Live coding: Architecture Review & Integration",
              "lead": "Ghép các mảnh đã xây rời rạc qua 7 bài thành một hệ thống chạy được:",
              "concept": "Ghép các mảnh đã xây rời rạc qua 7 bài thành một hệ thống chạy được:\n| Thành phần | Từ bài | Điểm tích hợp |\n| --- | --- | --- |\n| Prompt registry | Bài 1 | Service load prompt qua `registry().render(name, version=\"production\")` |\n| Eval pipeline | Bài 2 | `eval.run`  • `eval.gate` gọi được từ CLI và CI |\n| Cache 2 tầng | Bài 3 | Bọc quanh lời gọi LLM; key chứa `prompt_version` |\n| Container | Bài 4 | Image multi-stage, SSE endpoint, healthcheck |\n| Deploy | Bài 5 | VM + systemd + nginx + Secret Manager |\n| CI/CD | Bài 6 | `ci.yml`, `eval-gate.yml`, `cd.yml`  • branch protection |\n| Observability | Bài 7 | `record_cost()`  • tracing sampled + dashboard + alert |\nRà soát các \"đường nối\" hay vỡ:\n- Cache key có `prompt_version` không? (không thì rollback prompt vô nghĩa)\n- Eval gate có chạy khi PR đụng `src/rag/**`, không chỉ `prompts/**`?\n- Smoke test có gọi câu hỏi **có đáp án biết trước**, không chỉ `/health`?\n- Secret đọc lúc runtime, không nằm trong image?\n- Alert có người nhận thật (Slack/email), không chỉ log?",
              "codeLang": "text",
              "code": "",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-3-l8-t4",
              "title": "3. Pipeline hoàn chỉnh - checklist tích hợp",
              "lead": "- [ ] Version: prompt trong registry, có ≥ 2 version + changelog; dataset golden set được version hoá",
              "concept": "- [ ] **Version**: prompt trong registry, có ≥ 2 version + changelog; dataset golden set được version hoá\n- [ ] **Evaluate**: `eval.run --subset` chạy \\< 3 phút; `eval.gate` so baseline + có gate riêng cho slice `injection`/`out_of_scope`\n- [ ] **Register**: promote prompt = đổi alias `production`; rollback = trỏ alias về version cũ (không cần build)\n- [ ] **Deploy**: merge `main` → CI (lint + unit + eval) → CD (build tag=SHA → push → VM restart) → smoke test\n- [ ] **Monitor**: dashboard cost/feature + latency p95 + cache hit + hallucination rate + error/fallback; alert cost spike hoạt động\n- [ ] **Feedback loop**: có script/quy trình lấy câu bị feedback âm từ log → thêm vào `golden set` version kế tiếp",
              "codeLang": "text",
              "code": "",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-3-l8-t5",
              "title": "4. Checklist Production-Ready",
              "lead": "Đối chiếu trước khi coi hệ thống là \"xong\":",
              "concept": "Đối chiếu trước khi coi hệ thống là \"xong\":\n### Bảo mật & cấu hình\n- [ ] Không có API key nào ở dạng file trên VM hoặc trong image layer\n- [ ] Secret đọc từ Secret Manager lúc runtime; xoay key = `versions add` + restart\n- [ ] Port app không truy cập được từ Internet; chỉ 80/443 mở; SSH giới hạn IP\n### Chất lượng & thay đổi\n- [ ] Branch protection: không merge `main` khi CI hoặc eval-gate đỏ\n- [ ] Eval theo slice - chứng minh bắt được regression vô hình\n- [ ] Prompt lint chặn biến thiếu / version sai kiểu\n### Vận hành & phục hồi\n- [ ] Có đường rollback cho **cả 3 trục**: image tag (code), prompt version alias, model config\n- [ ] Smoke test tự chạy sau deploy; fail → tự rollback; đã diễn tập rollback thật\n- [ ] `last-known-good` được ghi lại sau mỗi smoke pass\n- [ ] Container tự restart khi crash (`systemd Restart=always`)\n- [ ] Backup vector index định kỳ + đã thử khôi phục\n### Chi phí & giám sát\n- [ ] Cost budget tháng + alert 50/80/100%\n- [ ] Hard limit cost per user / ngày\n- [ ] Dashboard production có người xem; alert có người nhận\n- [ ] Runbook cho ≥ 2 loại incident (khuyến nghị đủ 4: cost / hallucination / jailbreak / outage)\n- [ ] Fallback provider được cấu hình **và đã diễn tập**",
              "codeLang": "text",
              "code": "",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-3-l8-t6",
              "title": "5. Take-home",
              "lead": "1. Thêm 1 incident playbook vào runbook (chọn loại chưa viết ở Bài 7), gồm: tín hiệu phát hiện cụ thể (metric + ngưỡng), các bước khoanh vùng bằng dashboard hiện có, hành động giảm thiểu, mục \"sau sự cố\".",
              "concept": "1. **Thêm 1 incident playbook** vào runbook (chọn loại chưa viết ở Bài 7), gồm: tín hiệu phát hiện cụ thể (metric + ngưỡng), các bước khoanh vùng bằng dashboard hiện có, hành động giảm thiểu, mục \"sau sự cố\".\n2. **Thực hiện một lần rollback thật**: chọn prompt version alias **hoặc** image tag, rollback trên hệ thống đã deploy, ghi lại từng lệnh + thời gian từ lúc quyết định đến lúc dịch vụ ổn định.\n3. (Tùy chọn) Bổ sung **vòng feedback**: script lấy 10 câu bị thumbs-down gần nhất từ log, gán đáp án kỳ vọng, tạo `golden set` version mới, chạy lại eval để xem baseline có đổi.",
              "codeLang": "text",
              "code": "",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-3-l8-t7",
              "title": "6. Q&A Session",
              "lead": "Chủ đề gợi ý:",
              "concept": "Chủ đề gợi ý:\n- Khi nào một LLM app **đáng** self-host model thay vì gọi API (nhắc Bài 4).\n- Eval gate chặn nhầm PR tốt (judge nhiễu) - cân bằng `drop_tolerance` thế nào.\n- Chi phí thật của việc \"làm production đúng chuẩn\" cho team nhỏ - cắt gì được, cắt gì không.\n- Prompt registry hosted vs git-based cho team có PM chỉnh prompt.",
              "codeLang": "text",
              "code": "",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            },
            {
              "id": "module-3-l8-t8",
              "title": "Tóm tắt",
              "lead": "mermaid",
              "concept": "| Trụ cột | Cốt lõi |\n| --- | --- |\n| Pipeline chính | version → evaluate → register → deploy → monitor → feedback; không có \"train\" ở đường chính |\n| Tích hợp | Kiểm các \"đường nối\": cache key có prompt_version, eval-gate trigger đủ path, smoke test có đáp án biết trước |\n| Production-ready | Secret runtime · rollback 3 trục · smoke + auto-rollback · cost budget + alert · runbook + fallback đã diễn tập |\n| Feedback loop | Câu bị feedback âm → golden set version kế → baseline eval mới |",
              "codeLang": "mermaid",
              "code": "graph TB\n    subgraph \"Vòng lặp chính - KHÔNG có train\"\n        V[\"Version prompt/dataset\"] --> E[\"Evaluate - gate\"] --> R[\"Register - alias production\"] --> D[\"Deploy - CI/CD + smoke\"] --> M[\"Monitor - dashboard + alert\"]\n        M -->|feedback| V\n    end\n    M -.incident.-> PB[\"Playbook: cost / hallucination / jailbreak / outage\"]\n    FT[[\"Nhánh phụ: fine-tune LoRA<br>validate -> train -> eval -> register model\"]] -.model config.-> D",
              "tip": "Tham khảo tài liệu gốc trong LLM Engineer Handbook để xem toàn bộ chi tiết và hướng dẫn cấu hình chuyên sâu."
            }
          ]
        }
      ]
    }
  ]
};

// Freeze data to prevent mutation
Object.freeze(KNOWLEDGE_DATA);

/**
 * Helper: Tìm kiếm node theo ID
 */
function findNodeById(id) {
  if (id === 'root') return KNOWLEDGE_DATA;
  for (const mod of KNOWLEDGE_DATA.modules) {
    if (mod.id === id) return mod;
    for (const lesson of mod.lessons) {
      if (lesson.id === id) return lesson;
      for (const topic of lesson.topics) {
        if (topic.id === id) return topic;
      }
    }
  }
  return null;
}

/**
 * Helper: Tìm kiếm tất cả topics phù hợp với từ khóa
 */
function searchTopicsByKeyword(keyword) {
  if (!keyword || !keyword.trim()) return [];
  const term = keyword.toLowerCase().trim();
  const results = [];

  for (const mod of KNOWLEDGE_DATA.modules) {
    for (const lesson of mod.lessons) {
      for (const topic of lesson.topics) {
        const inTitle = topic.title.toLowerCase().includes(term);
        const inLead = (topic.lead || '').toLowerCase().includes(term);
        const inConcept = (topic.concept || '').toLowerCase().includes(term);
        const inLesson = lesson.title.toLowerCase().includes(term);

        if (inTitle || inLead || inConcept || inLesson) {
          results.push({
            moduleId: mod.id,
            moduleTitle: mod.title,
            lessonId: lesson.id,
            lessonTitle: lesson.title,
            topic: topic,
            matchedField: inTitle ? 'title' : (inLesson ? 'lesson' : 'content')
          });
        }
      }
    }
  }
  return results;
}

/**
 * Helper: Thống kê tổng số lượng bài học và chủ đề
 */
function getKnowledgeStats() {
  return KNOWLEDGE_DATA.metadata;
}

// Export for module or browser window
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { KNOWLEDGE_DATA, findNodeById, searchTopicsByKeyword, getKnowledgeStats };
}
