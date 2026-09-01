# agent_stat

Chatbot thống kê Text-to-SQL, multi-agent — Phase 1 theo "Ý tưởng Agent.docx"
(khung Agent thống kê: đọc schema trước, sinh SQL SELECT read-only trả lời
câu hỏi thống kê tự nhiên).

## Kiến trúc

```
START → guardrail_input → stat_agent → reply → guardrail_output → END
```

- `app/stat_agent/` — ReAct worker, 3 tool (`get_db_schema`, `run_sql_select`,
  `list_khu_vuc`), đọc-only trên bảng demo `luot_ra_vao` (SQLite).
- `app/supervisor_agent/` — hub: guardrail input/output + gọi stat_agent.
- `app/guardrails/` — injection/toxic chặn cứng, topic scope, PII redact.

## Chạy

```bash
pip install -r requirements.txt
cp .env.example .env   # điền OPENAI_API_KEY
uvicorn app.main:app --reload --app-dir .
```

Mở http://localhost:8000 (demo UI) hoặc http://localhost:8000/docs (API).

## Test

```bash
pytest
```

Không có `OPENAI_API_KEY` (hoặc chạy dưới pytest) → agent chạy offline, giả
1 tool_call thay vì gọi OpenAI thật.

## Lộ trình tiếp theo (chưa làm ở Phase 1)

Theo tài liệu ý tưởng: Phase 2 (materialized views, guardrail nâng cao, HITL,
tracing/eval), Phase 3 (Visualization Agent), Phase 4 (phân quyền phòng ban).
