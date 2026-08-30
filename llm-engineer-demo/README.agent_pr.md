# agent_pr — Hierarchical VN-stock

Pipeline: giá (vnstock) + tin (CafeF) + eval từ khoá + ghép câu. **Không cần OpenAI.**

Mã demo: **VNM, HPG, FPT, VCB**.

---

## Chạy bằng Docker Compose (cách chính)

Từ thư mục `llm-engineer-demo`:

```bash
cd vn-stock-swarm/llm-engineer-demo
docker compose up --build
```

Chỉ API (không Qdrant):

```bash
docker compose up --build app
```

Mở <http://localhost:8000/docs> → **POST /pr/ask**.

```bash
curl -s -X POST http://localhost:8000/pr/ask ^
  -H "Content-Type: application/json" ^
  -d "{\"symbol\":\"HPG\"}"
```

Git Bash / Linux:

```bash
curl -s -X POST http://localhost:8000/pr/ask \
  -H "Content-Type: application/json" \
  -d '{"symbol":"HPG"}'
```

Chỉ giá: `POST /pr/price` cùng body `{"symbol":"HPG"}`.

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
POST /pr/ask
    → coordinator
        đợt 1 (song song): PriceAgent · NewsAgent · DBAgent
        → after_wave1 (fan-in) → coordinator
        đợt 2a: EvalAgent → coordinator
        đợt 2b: SynthesisAgent → coordinator
        → reply (hub trả user)
    → { answer, trace, last, pct_change, n_news }
```

LangFuse (`MONITORING_ENABLED=true`): span cha `agent_pr_ask` + span con từng node
(`coordinator`, `craw_*`, `news_*`, `db_*`, `eval_score`, `synth_compose`, `reply`).
`POST /pr/price` → `agent_pr_price`.

Chấm chất lượng (LLM-as-judge, 2 chiều như `app/agent_m2/eval.py`):

```bash
curl -s -X POST http://localhost:8000/pr/ask/evaluate \
  -H "Content-Type: application/json" \
  -d '{"symbol":"HPG"}'
```

→ `task_success` + `trajectory` (efficiency / logical_order / tool_correctness /
recovery) + `trajectory_steps`. Tốn 2 lời gọi LLM — không gộp vào `/pr/ask`.


Đối chiếu: [Simplize HPG](https://simplize.vn/co-phieu/HPG), [CafeF HPG](https://cafef.vn/du-lieu/hose/hpg-cong-ty-co-phan-tap-doan-hoa-phat.chn).

---

## Pytest (tuỳ chọn, kiểm tra code)

```bash
python -m pytest tests/test_supervisor_agent.py -s -q
```

Không dùng pytest để “chạy app”.
