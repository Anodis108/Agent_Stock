# Test Plan — V2 Clean Agents + Docker Product

Nguyên tắc giữ từ vòng Quality Loop: **chất lượng trước**, không nới scorer.
V2 thêm gate kiến trúc + Langfuse lồng nhau + **chỉ test qua Docker** (product).

### Pytest (7 file) — dependency thật

- Không `fakes.py` / mock business deps (vnstock, Cafef, LLM, SQLite).
- Cần `.env` (`OPENAI_API_KEYS`), network; ~2 phút / full suite.
- `pytest.skip` khi vnstock tạm không khả dụng.

```bash
cp .env.example .env
python -m pytest tests/ -q
docker compose run --rm ai pytest tests/ -q
```

## 1. Eval & golden (chuyển khỏi `scripts/`)

### Nguồn

- `specs/eval/golden_dataset.yaml` (30 case).
- Runner mới (Phase 15): `python -m src.portfolio_watch.eval.run`.
- Docker: `docker compose run --rm ai python -m src.portfolio_watch.eval.run --case-id lookup_01`

### Tiêu chí pass (giữ)

- Rule-based `must_include` / `must_not_include`.
- Injection: **100%** pass.
- Lookup/comparison: judge (nếu bật) + `task_success.success == true`.
- Trajectory: cảnh báo nếu overall < 3.0; MVP không fail case chỉ vì trajectory.

### Regression

```bash
docker compose run --rm ai python -m src.portfolio_watch.eval.regression
```

- Không tụt quá `REGRESSION_TOLERANCE` (0.05) so với baseline 30/30.
- Chạy sau Phase 13 (graph thật) và sau Phase 15 (xóa scripts).

## 2. Kiến trúc agent (Phase 12)

Mỗi agent folder — checklist thủ công / pytest:

| Agent | Test tối thiểu |
|---|---|
| `price_agent` | fetch close + change_pct deterministic |
| `news_agent` | ReAct gọi tool, lọc tin theo symbol |
| `event_classifier` | normal vs abnormal routing |
| `eval_agent` | severity + evidence |
| `supervisor_agent` | rewrite + agents_to_call |
| `answer_composer` | guardrail loop, grounding |
| `synthesis_agent` | alert draft + guardrail |

```bash
docker compose run --rm ai pytest tests/ -q
# 7 file: test_docker, test_backend, test_ai, test_agents, test_eval, test_tracing, test_frontend
```

## 3. LangGraph (Phase 13)

- Graph compile không lỗi.
- Node list khớp `specs/agents.md`.
- 1 invoke chat stub → trả `steps[]` có thứ tự hợp lý.
- Export graph: `docker compose run --rm ai python -m src.portfolio_watch.graph.workflow`
  → `docs/agent_graph.png`.

## 4. Langfuse trace lồng nhau (Phase 14)

### Điều kiện

- Langfuse self-host chạy tại host `:3000`.
- `.env`: `MONITORING_ENABLED=true`, keys hợp lệ.
- AI container: `LANGFUSE_HOST=http://host.docker.internal:3000`.

### Checklist thủ công (bắt buộc trước khi đóng Phase 14)

1. `docker compose up --build` (frontend + backend + ai).
2. Mở Frontend → gửi 1 câu hỏi chat (vd. "Giá FPT hôm nay?").
3. Mở Langfuse UI `http://localhost:3000` → Traces.
4. Xác nhận:
   - [ ] **Đúng 1 trace** cho câu hỏi đó (không 2 trace trùng request).
   - [ ] Trace name / metadata có `request_id` hoặc câu hỏi tóm tắt.
   - [ ] Expand trace → thấy span `rewrite_question`, `supervisor`, …
   - [ ] Trong span agent (vd. `news_agent`) → span con thụt 1 cấp
         (`fetch_news`, `react_turn_1`, …) — **tên rõ**, có input/output.
   - [ ] Không span rỗng (output null hàng loạt).

### Automated

- pytest `test_tracing.py`: no-op khi `MONITORING_ENABLED=false` + chat 200 với
  deps thật (không mock Langfuse client).
- Hierarchy parent/child span: **checklist thủ công** trên Langfuse UI (mục 4).

### No-op

- `MONITORING_ENABLED=false` → chat 200; pytest assert response OK (không assert
  mock Langfuse).

## 5. Docker product (Phase 15)

```bash
docker compose up --build -d
curl -sf http://localhost:8000/health
curl -sf http://localhost:8001/health
# Frontend: http://localhost:5173
docker compose down
```

- [x] Không file nào trong `scripts/` còn được README tham chiếu.
- [ ] Backend health + chat proxy OK khi AI healthy.
- [ ] AI down → Backend trả lỗi rõ (giữ test Phase 5).

## 6. End-to-end demo (Phase 16)

Trên máy có `.env` + (tuỳ chọn) Langfuse:

1. `docker compose up --build`
2. Thêm mã watchlist → quét → duyệt nếu pending.
3. Chat 1 câu → timeline bước + câu trả lời.
4. (Nếu monitoring bật) Langfuse 1 trace như mục 4.

Ghi kết quả ngắn vào `specs/change-log.md`.
