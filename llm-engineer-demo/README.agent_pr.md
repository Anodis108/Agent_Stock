# agent_pr — Hierarchical VN-stock

Pipeline: hub LLM chọn worker → giá (vnstock) / tin (CafeF) / DB / eval / ghép câu.
**POST `/pr/ask` cần OpenAI** (`OPENAI_API_KEYS` trong `.env`). `POST /pr/price` không cần.

Mã: mọi CP niêm yết VN (HOSE / HNX / UPCOM), không whitelist.

---

## Chạy bằng Docker Compose (cách chính)

Từ thư mục `llm-engineer-demo` (compose đọc `.env`):

```bash
cd vn-stock-swarm/llm-engineer-demo
docker compose up --build
```

Chỉ API (không Qdrant):

```bash
docker compose up --build app
```

Mở <http://localhost:8000/> (UI agent_pr) hoặc <http://localhost:8000/docs> → **POST /pr/ask**.

```bash
curl -s -X POST http://localhost:8000/pr/ask ^
  -H "Content-Type: application/json" ^
  -d "{\"question\":\"Tại sao HPG giảm?\",\"thread_id\":\"sess-1\"}"
```

Git Bash / Linux:

```bash
curl -s -X POST http://localhost:8000/pr/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"Tại sao HPG giảm?","thread_id":"sess-1"}'
```

Chỉ mã (hub tự hỏi phân tích đủ worker): `{"symbol":"HPG","thread_id":"sess-1"}`.

Chỉ giá, không qua hub: `POST /pr/price` cùng body `{"symbol":"HPG"}`.

Dừng: `docker compose down`.

---

## Vẽ graph supervisor

Từ `llm-engineer-demo` (giống `python -m app.agent_m2.multi_agent.hierarchical`):

```bash
cd vn-stock-swarm/llm-engineer-demo
python -m app.agent_pr.supervisor_agent.graph
```

In ra đường dẫn: `images/supervisor_agent_graph.png` (cần mạng, mermaid.ink).
Dùng `get_graph(xray=True)` — bung node bên trong từng worker.
Lỗi mạng → `images/supervisor_agent_graph.mmd` — dán [mermaid.live](https://mermaid.live).

---

## Không Docker

```bash
uvicorn app.main:app --reload
```

Cùng URL `/pr/ask` như trên.

---

## Luồng

Hierarchical Coordinator (hub) — worker là subgraph, không gọi nhau:

```
POST /pr/ask  {question, thread_id, user_id?}
    → recall (long-term theo user_id; ghi history user)
    → coordinator (LLM bind need_* tools → AgentPlan; có history + memories)
        gather (song song, chỉ worker plan bật; tái dùng giá/tin ĐÚNG MÃ)
        → after_wave1 (fan-in) → coordinator
        EvalAgent  — nếu plan bật và đã có giá+tin (mỗi lượt hỏi mới)
        SynthesisAgent — nếu plan bật (mỗi lượt hỏi mới)
        → reply → store (trích 1 sự thật dài hạn nếu có user_id)
    → { answer, trace, used_agents, plan_reasoning, thread_id, user_id, … }
```

Mỗi worker (và coordinator) là ReAct giống `agent_m2`: LLM `bind_tools` trên
catalog **riêng** (sau `select_tools` embedding), `ToolNode` chạy tool, `pack`
đưa về hợp đồng hub. HITL ghi DB vẫn chỉ ở hub `interrupt_before=["hitl_commit"]`.

**Memory** (cùng mô hình Module II / `agent_m2`):

- **Short-term:** `thread_id` (client bắt buộc gửi, giống `/assistant`) + `PostgresSaver`. UI giữ id trong `localStorage`. Cùng phiên: nhớ hội thoại; giá/tin cùng mã không crawl lại. Nút **Phiên mới** đổi `thread_id`. Compose bật Postgres; thiếu `thread_id` → 422.
- **Long-term:** `user_id` + `app.agent_pr.memory` (Qdrant collection `user_memory`). Không `user_id` → không recall/store. `docker compose --profile rag up` bật Qdrant; không Qdrant / không embed thì store fallback in-memory.

```bash
curl -s -X POST http://localhost:8000/pr/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"Tại sao HPG giảm?","thread_id":"sess-1","user_id":"alice"}'
```

LangFuse (`MONITORING_ENABLED=true`): span cha `agent_pr_ask` + span con từng node
(`coordinator`, `craw_*`, `news_*`, `db_*`, `eval_score`, `synth_compose`, `reply`).
`POST /pr/price` → `agent_pr_price`.

Chấm chất lượng (LLM-as-judge, 2 chiều như `app/agent_m2/eval.py`):

```bash
curl -s -X POST http://localhost:8000/pr/ask/evaluate \
  -H "Content-Type: application/json" \
  -d '{"question":"Tại sao HPG giảm?","thread_id":"sess-1"}'
```

→ `task_success` + `trajectory` (efficiency / logical_order / tool_correctness /
recovery) + `trajectory_steps`. Tốn 2 lời gọi LLM — không gộp vào `/pr/ask`.


Đối chiếu: [Simplize HPG](https://simplize.vn/co-phieu/HPG), [CafeF HPG](https://cafef.vn/du-lieu/hose/hpg-cong-ty-co-phan-tap-doan-hoa-phat.chn).

---

## Pytest (tuỳ chọn, kiểm tra code)

```bash
python -m pytest tests/test_supervisor_agent.py tests/test_supervisor_memory.py -s -q
```

Không dùng pytest để “chạy app”.
