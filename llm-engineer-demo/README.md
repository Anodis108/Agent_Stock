# LLM Engineer — Demo Codebase

Codebase thực hành xuyên suốt khoá **LLM Engineer**, xây dựng dần theo từng buổi học,
gồm 2 module độc lập trên cùng 1 FastAPI app:

| Module | Chủ đề | Chi tiết |
|--------|--------|----------|
| **Module I** | Vietnamese Legal Assistant — RAG Chatbot (chat completions → RAG → agentic RAG → eval/guardrails → production optimization) | [README.module1.md](README.module1.md) |
| **Module II** | AI Agent — Personal Assistant (LangGraph: ReAct loop, HITL, memory, context engineering, tool design, MCP) | [README.module2.md](README.module2.md) |
| **agent_pr** | Hierarchical VN-stock — giá + tin + eval + synthesis (`app/agent_pr/`) | [README.agent_pr.md](README.agent_pr.md) |

> **Triết lý:** dùng **native SDK** (OpenAI, Qdrant...) thay vì framework cao cấp, để
> engineer hiểu và kiểm soát từng lời gọi. **API-first** với FastAPI. LangGraph (Module I
> Buổi 6, Module II) là ngoại lệ có chủ đích — chỉ orchestrate control flow, xem giải
> thích trong từng README module.

---

## Cài đặt

```bash
conda create -n llm-engineer python==3.10
pip install -r requirements.txt

cp .env.example .env
# Mở .env, điền OPENAI_API_KEYS (một hoặc nhiều key, ngăn cách bằng dấu phẩy)
```

## Chạy

```bash
uvicorn app.main:app --reload
```

- Docs tương tác: <http://localhost:8000/docs>
- Health check (không cần key): <http://localhost:8000/health>
- **Demo UI**: <http://localhost:8000/> — Hierarchical VN-stock (`app/static/agent_pr.html`).
  Module I chat cũ: <http://localhost:8000/legal-chat> (`chat.html`).
  Portfolio: <http://localhost:8000/portfolio>.
  Lịch sử chat lưu `localStorage`. Bấm **"Ingest dữ liệu"** trước khi hỏi RAG —
  với `QDRANT_URL=:memory:` mỗi process có Qdrant riêng; nút này gọi `POST /admin/ingest`.
  Toggle **Streaming** (`/chat/stream`) và **Agent (CRAG)** (`/chat/agent`).
  Module II: `/assistant/message` + `/assistant/approve` — [README.module2.md](README.module2.md).

## Test

```bash
pytest          # không gọi API thật (mock LLM), không cần key
```

Test cho cả 2 module nằm chung trong `tests/` (`test_chat.py`, `test_rag.py`,
`test_agent.py`, ... cho Module I; `test_agent_m2*.py` cho Module II).

**agent_pr** (Hierarchical VN-stock; `/pr/ask` cần OpenAI để hub chọn worker) — Docker Compose:

```bash
docker compose up --build app
# POST http://localhost:8000/pr/ask  {"question":"Tại sao HPG giảm?"}
```

Chi tiết: [README.agent_pr.md](README.agent_pr.md).

---

## Cấu trúc tổng quan

```
Modelfile              # Module I, Buổi 2 — Ollama model có sẵn persona pháp lý
app/
├── config.py          # đọc .env (điểm duy nhất chạm secrets, dùng chung 2 module)
├── main.py            # FastAPI app + phục vụ static tại "/"
├── pipeline.py         # Module I — orchestrator: retrieve → prompt → llm
├── static/             # agent_pr.html, chat.html, portfolio, swarm-handoff-map
├── api/                 # FastAPI routes + schemas (routes_chat/routes_admin: Module I;
│                        #   routes_assistant: Module II)
├── llm/                 # Module I — native SDK: completion, streaming, backoff, key rotation
├── prompts/              # Module I — role prompting, few-shot, chèn context RAG
├── schemas/              # Module I — Pydantic structured output
├── tools/                # Module I, Bài 1 — function calling viết tay
├── retrieval/            # Module I — RAG hoàn chỉnh (loader, chunking, embeddings, vectorstore, retriever)
├── agent/                # Module I, Buổi 6 — CRAG + Query Decomposition (LangGraph)
├── agent_m2/             # Module II — Personal Assistant agent (LangGraph) — chi tiết ở README.module2.md
├── agent_pr/             # Hierarchical VN-stock — README.agent_pr.md
├── guardrails/           # Module I — injection.py, pii.py, checks.py
├── eval/                 # Module I — judge.py (LLM-as-Judge), ragas_native.py, metrics.py
├── monitoring/           # Module I — tracing.py, LangFuse hooks tối thiểu
└── optimization/         # Module I — prompt_cache.py, caching.py, routing.py
```

Chi tiết từng buổi học, từng file, ví dụ curl: xem
[README.module1.md](README.module1.md) và [README.module2.md](README.module2.md).

> **Bảo mật:** `.env` đã nằm trong `.gitignore`. Không bao giờ commit API key.
