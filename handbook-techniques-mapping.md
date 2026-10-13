# Ánh xạ kỹ thuật LLM-Engineer-Handbook → VN Stock Swarm

Đối chiếu nội dung 3 module của `D:\Hoc_Tap\YOURClass\LLM-Engineer-Handbook` với mã nguồn hiện tại của `vn-stock-swarm`.
Mức độ: ✅ đã dùng thực sự · 🟡 dùng một phần / biến thể · ❌ chưa dùng.

---

## Module I — LLM, Prompt, RAG & Vector DB

| Bài / Kỹ thuật (Handbook) | Mức | Dùng ở đâu trong code | Ghi chú |
|---|---|---|---|
| **B1.1 Chat Completions** | ✅ | [src/backend/infra/llm/completion.py](src/backend/infra/llm/completion.py) — `chat()` | Bọc `client.chat.completions.create` |
| **B1.2 Parameters (temperature, max_tokens, top_p)** | ✅ | [src/backend/infra/llm/params.py](src/backend/infra/llm/params.py) (`GenerationParams`, `DETERMINISTIC`), [resources/configs/config.yaml](resources/configs/config.yaml) mục `llm` | Mọi brain dùng `DETERMINISTIC` |
| **B1.3 Streaming** | ✅ | `chat_stream()` trong [completion.py](src/backend/infra/llm/completion.py); `LlmAnswerDraftBrain.compose(on_token=...)` trong [answer_composer/nodes.py](src/backend/agents/answer_composer/nodes.py) | Token đẩy ra SSE |
| **B1.4 Rate limit – Exponential Backoff** | ✅ | `retry_with_backoff` trong [src/backend/infra/llm/resilience.py](src/backend/infra/llm/resilience.py); `_post_json` (backoff + jitter) trong [client.py](src/backend/infra/llm/client.py) | |
| **B1.4 API Key Rotation** | ✅ | `RotatingKeyPool` trong [resilience.py](src/backend/infra/llm/resilience.py); `mark_current_key_limited` trong [client.py](src/backend/infra/llm/client.py) | Key 429 bị cooldown 60s |
| **B1.5 Prompt patterns (role, zero-shot)** | 🟡 | Template trong [resources/prompts/](resources/prompts/) | Chủ yếu role + zero-shot, không thấy few-shot/CoT rõ ràng |
| **B1.6 Structured Outputs (Pydantic)** | ✅ | `chat_parsed()` (`completions.parse(response_format=schema)`) trong [completion.py](src/backend/infra/llm/completion.py); `call_llm_structured`, `extract_json_str` trong [structured.py](src/backend/infra/llm/structured.py); schema: `RewriteOutput`, `SupervisorOutput` ([supervisor_agent/schemas.py](src/backend/agents/supervisor_agent/schemas.py)), `EvalSeverityOutput`, `MemoryFact` ([shared/schemas.py](src/backend/shared/schemas.py)) | Có fallback heuristic khi parse fail |
| **B1.7 Function Calling** | 🟡 | `chat_with_tools()` trong [completion.py](src/backend/infra/llm/completion.py) | Có hàm nhưng các agent gọi tool bằng Python trực tiếp (News ReAct dùng structured output để quyết định, không dùng `tools=`) |
| **B2 Local LLM serving (Ollama / vLLM, OpenAI-compatible)** | ✅ | Backend `openai/ollama/vllm` trong [backends.py](src/backend/infra/llm/backends.py), `get_client()` đổi `base_url` trong [client.py](src/backend/infra/llm/client.py); [Modelfile](Modelfile) | ⚠️ `Modelfile` vẫn là persona "Vietnamese Legal Assistant" từ bài tập cũ, chưa đổi sang chứng khoán |
| **B3 Fine-tuning LoRA/QLoRA** | ❌ | — | Không fine-tune |
| **B4 Embeddings** | ✅ | `embed_question` (OpenAI `text-embedding-3-small` hoặc trigram offline) trong [cache/semantic.py](src/backend/infra/cache/semantic.py); `_embed_passages` trong [long_term_memory.py](src/backend/infra/storage/long_term_memory.py) | |
| **B4 Similarity metrics (cosine)** | ✅ | `cosine_similarity` trong [cache/semantic.py](src/backend/infra/cache/semantic.py) | Ngưỡng 0.93 |
| **B4 Vector Database** | ✅ | Qdrant (`QdrantClient`, `_ensure_collection`) trong [long_term_memory.py](src/backend/infra/storage/long_term_memory.py) | Fallback in-memory khi không có Qdrant/key |
| **B5 RAG Pipeline (ingestion → retrieval → generation)** | 🟡 | Không có RAG trên tài liệu; tương đương "retrieval từ tool": Price/News agent lấy dữ liệu → `build_evidence` → Composer sinh câu trả lời grounded ([answer_composer/nodes.py](src/backend/agents/answer_composer/nodes.py)) | Không chunking/ingestion PDF |
| **B6 Query Decomposition** | ✅ | `_decompose_query` trong [supervisor_agent/nodes.py](src/backend/agents/supervisor_agent/nodes.py) | Tách câu so sánh đa mã / giá + tin |
| **B6 Query rewrite (coreference)** | ✅ | `HeuristicRewriteBrain`, `LlmRewriteBrain`, `_apply_memory_symbol` trong [supervisor_agent/nodes.py](src/backend/agents/supervisor_agent/nodes.py); prompt [rewrite_question](resources/prompts/rewrite_question/) | |
| **B6 Self-RAG / CRAG** | 🟡 | Vòng "draft → kiểm tra → viết lại" trong `run_answer_composer` (tối đa 3 lần) | Tinh thần self-correction, không phải CRAG đúng nghĩa |
| **B6 LangGraph basics (StateGraph, conditional edges)** | ✅ | `build_chat_graph` trong [graph/chat.py](src/backend/graph/chat.py), `build_scan_graph` trong [graph/scan.py](src/backend/graph/scan.py); state: [graph/state.py](src/backend/graph/state.py) | |
| **B7 Input Guardrail (injection, out-of-scope)** | ✅ | `check_input_guardrail` trong [domain/guardrails/input_guardrail.py](src/backend/domain/guardrails/input_guardrail.py) | Rule/regex, chưa có LLM-based detection |
| **B7 Output Guardrail (grounding, cấm khuyến nghị)** | ✅ | `check_output`, `has_evidence_grounding`, `rewrite_keep_grounding`, `strip_buy_sell` trong [output_checks.py](src/backend/domain/guardrails/output_checks.py) | Kiểm tra con số phải có trong evidence |
| **B7 PII redaction (regex)** | ✅ | `redact_pii`, `sanitize_trace_payload` trong [monitoring/tracing.py](src/backend/infra/monitoring/tracing.py) | Không dùng Presidio |
| **B7 Evaluation metrics (BLEU/ROUGE/RAGAS)** | ❌ | — | Dùng rule-based + LLM judge thay thế (xem Module III) |
| **B7 Monitoring LangFuse** | ✅ | `trace_request`, `agent_span`, `agent_step` trong [tracing.py](src/backend/infra/monitoring/tracing.py) | |
| **B8 Semantic Caching** | ✅ | `SemanticCache`, `try_semantic_cache_get`, `is_dynamic_question` trong [cache/semantic.py](src/backend/infra/cache/semantic.py) | Bỏ qua câu hỏi có ngày/giá động |
| **B8 Prompt caching (prefix tĩnh lên đầu)** | 🟡 | Template YAML đặt hướng dẫn tĩnh trước, biến động sau | Không cấu hình gì thêm |
| **B8 Model Routing** | ✅ | `select_answer_model` (gpt-4o-mini ↔ gpt-4o theo severity/confidence) trong [answer_composer/nodes.py](src/backend/agents/answer_composer/nodes.py) | Routing theo rule, không dùng embedding centroid/classifier |
| **B9 Capstone: Gradio UI / HF Spaces** | ❌ (thay thế) | Web UI riêng: [src/frontend/](src/frontend/) (`index.html`, `app.js`) | |

---

## Module II — AI Agent

| Bài / Kỹ thuật (Handbook) | Mức | Dùng ở đâu trong code | Ghi chú |
|---|---|---|---|
| **B1 Core components (LLM + tools + memory + planning)** | ✅ | Toàn bộ [src/backend/agents/](src/backend/agents/) | |
| **B1 System prompt / AGENTS.md** | ✅ | [AGENTS.md](AGENTS.md), [CLAUDE.md](CLAUDE.md) (cho coding agent) | |
| **B1 ReAct paradigm** | ✅ | `LlmNewsBrain.decide` + vòng `run_news_agent` ([news_agent/nodes.py](src/backend/agents/news_agent/nodes.py), prompt [news_agent_react](resources/prompts/news_agent_react/)); EvalAgent quyết định `needs_history` → gọi tool `read_price_history` ([eval_agent/nodes.py](src/backend/agents/eval_agent/nodes.py), [eval_agent/tools.py](src/backend/agents/eval_agent/tools.py)) | |
| **B2 State, Nodes, Edges** | ✅ | `ChatState`, `ScanState` ([graph/state.py](src/backend/graph/state.py)); `route_after_guardrail`, `route_from_supervisor` ([graph/chat.py](src/backend/graph/chat.py)); `_route_after_classifier/eval/synthesis` ([graph/scan.py](src/backend/graph/scan.py)) | |
| **B2 Loop termination & error recovery** | ✅ | `recursion_limit=25` ([chat.py](src/backend/graph/chat.py), [scan.py](src/backend/graph/scan.py)); try/except fallback ở mọi brain (`route_question`, `rewrite_question`, `run_eval_agent`…) | |
| **B2 Plan/Act separation** | 🟡 | Rewrite + Supervisor (lập kế hoạch: chọn agents) → workers (thực thi) | |
| **B2 Memory & state persistence** | 🟡 | Lưu hội thoại SQLite (`memory_store.append_conversation`) | Không dùng LangGraph checkpointer/`thread_id` |
| **B2 Human-in-the-Loop** | ✅ | Gate1/Gate2 `pending_approval` trong [graph/scan.py](src/backend/graph/scan.py), [application/scan_symbol.py](src/backend/application/scan_symbol.py); duyệt/từ chối: [application/review_approval.py](src/backend/application/review_approval.py), [api/routers/approvals.py](src/backend/api/routers/approvals.py); feedback 👍/👎: [api/routers/hitl.py](src/backend/api/routers/hitl.py), [services/hitl_service.py](src/backend/services/hitl_service.py) | HITL kiểu lưu sự kiện chờ duyệt, không dùng `interrupt_before` của LangGraph |
| **B3 Short-term memory (sliding window + TTL)** | ✅ | `apply_sliding_window_with_ttl_eviction`, `filter_conversation_history` trong [infra/storage/memory_store.py](src/backend/infra/storage/memory_store.py); tham số `memory.short_term_window/ttl` trong [config.yaml](resources/configs/config.yaml) | 20 tin, 60 phút |
| **B3 Long-term memory (vector, theo user_id)** | ✅ | `recall_memory`, `store_memory`, `_extract_long_term_fact` ([supervisor_agent/nodes.py](src/backend/agents/supervisor_agent/nodes.py)); `save_to_long_term`, `recall_long_term` ([long_term_memory.py](src/backend/infra/storage/long_term_memory.py)); prompt [memory_fact](resources/prompts/memory_fact/) | Fact extraction bằng LLM, fallback heuristic |
| **B3 Context compression / context rot** | 🟡 | Chỉ cắt window + TTL; Composer chỉ nhận evidence tóm tắt (`_price_summary`, `_news_summary`) | Không có summarization/compaction |
| **B4 Tool design (atomic, schema rõ, idempotent)** | ✅ | Ports/Protocol: [domain/ports.py](src/backend/domain/ports.py); adapter: `VnstockPriceSource` ([price_source.py](src/backend/infra/market_data/price_source.py)), `CafefNewsSource`, `VnstockNewsSource`, `MultiSourceNewsSource` ([news_source.py](src/backend/infra/market_data/news_source.py)); `validate_symbol` | Có TTL cache, fallback offline |
| **B4 Tool selection (mỗi agent ≤ 5 tool, route tới chuyên gia)** | ✅ | Supervisor chọn `agents_to_call` ∈ {price, news, eval, chart, diagram, portfolio_watch} | |
| **B4 Tool security** | 🟡 | `validate_symbol`, chặn mã nước ngoài ở guardrail, cô lập dữ liệu theo `user_id` ([api/deps.py](src/backend/api/deps.py) `get_current_user_id`) | |
| **B4 MCP** | ❌ | — | |
| **B5 Agent eval: task success, trajectory** | ✅ | `evaluate_task_success`, `evaluate_trajectory` ([infra/eval/agent_scorers.py](src/backend/infra/eval/agent_scorers.py)); `score_routing`, `score_query_decomposition`, `score_groundedness` ([eval/agent_eval.py](src/backend/eval/agent_eval.py)); prompts `eval_task_success`, `eval_trajectory` | Báo cáo: [resources/eval/agent_eval_report.md](resources/eval/agent_eval_report.md) |
| **B5 Observability (trace từng node)** | ✅ | `agent_span` bọc mỗi node; `build_steps_from_chunks` ([graph/steps.py](src/backend/graph/steps.py)); sự kiện `node_start/node_finish` qua `emit_agent_event` → Live Agent Graph trên UI | |
| **B6 Multi-agent: Supervisor pattern** | ✅ | `supervisor_node` + `workers_node` ([graph/chat.py](src/backend/graph/chat.py)); `LlmSupervisorBrain` ([supervisor_agent/nodes.py](src/backend/agents/supervisor_agent/nodes.py)); prompt [supervisor_routing](resources/prompts/supervisor_routing/) | |
| **B6 Chạy worker song song** | ✅ | `ThreadPoolExecutor` trong `workers_node` ([chat.py](src/backend/graph/chat.py)) và `_node_fetch` ([scan.py](src/backend/graph/scan.py)) | |
| **B6 Chuyên gia hoá agent** | ✅ | `price_agent`, `news_agent`, `eval_agent`, `event_classifier`, `synthesis_agent`, `chart_agent.py`, `diagram_agent`, `portfolio_watch_agent`, `answer_composer` trong [src/backend/agents/](src/backend/agents/) | |

---

## Module III — Production LLMOps

| Bài / Kỹ thuật (Handbook) | Mức | Dùng ở đâu trong code | Ghi chú |
|---|---|---|---|
| **B1 Prompt versioning & templates** | ✅ | [resources/prompts/\<name\>/v1.yaml, v2.yaml](resources/prompts/) (metadata: version, model, owner, changelog, eval_score) | |
| **B1 Prompt Registry (alias `production`)** | ✅ | `registry().render(...)` trong [infra/llm/prompt_registry.py](src/backend/infra/llm/prompt_registry.py); file `production.txt` trong từng thư mục prompt | Không prompt hardcode trong agent |
| **B1 Prompt A/B testing** | ✅ | `pick_prompt_version` ([prompt_experiment.py](src/backend/infra/llm/prompt_experiment.py)), dùng trong `run_answer_composer`; cấu hình `prompt_ab_*` trong [config.yaml](resources/configs/config.yaml); so sánh: [scripts/compare_prompt_versions.py](scripts/compare_prompt_versions.py) | Ghi `prompt_version` vào cost context |
| **B1 Prompt lint trong CI** | ✅ | [infra/llm/prompt_lint.py](src/backend/infra/llm/prompt_lint.py); bước "Prompt lint" trong [.github/workflows/ci.yml](.github/workflows/ci.yml) | |
| **B2 Golden dataset** | ✅ | [resources/eval/golden_v6_comprehensive.yaml](resources/eval/golden_v6_comprehensive.yaml) (20 case/10 slice), `golden_v5.yaml`, `golden_pr_subset.yaml` | |
| **B2 Eval methods: rule-based + LLM-as-judge** | ✅ | `score_rule_based`, `score_llm_judge` trong [eval/run.py](src/backend/eval/run.py); prompt [eval_judge](resources/prompts/eval_judge/) | Có eval cache: [eval/eval_cache.py](src/backend/eval/eval_cache.py) |
| **B2 Slice-based eval** | ✅ | `SliceScore` trong [eval/run.py](src/backend/eval/run.py); test [tests/e2e/test_golden_v6_slices.py](tests/e2e/test_golden_v6_slices.py) | |
| **B2 Regression testing** | ✅ | [eval/regression.py](src/backend/eval/regression.py), [eval/history.py](src/backend/eval/history.py) | |
| **B2 CI Eval Gate** | ✅ | `check_gates` (baseline − drop_tolerance) trong [eval/gate.py](src/backend/eval/gate.py); workflow [.github/workflows/eval-gate.yml](.github/workflows/eval-gate.yml); diễn tập: [scripts/eval_gate_drill.py](scripts/eval_gate_drill.py), [scripts/eval_noise_calibration.py](scripts/eval_noise_calibration.py) | |
| **B2 HITL → Golden (data flywheel)** | ✅ | [scripts/export_hitl_feedback.py](scripts/export_hitl_feedback.py), [scripts/hitl_to_golden_draft.py](scripts/hitl_to_golden_draft.py) | |
| **B3 Token economics & đo trước khi tối ưu** | ✅ | `CostTracker`, `record_completion_usage` ([infra/cost/tracker.py](src/backend/infra/cost/tracker.py)); [scripts/cost_baseline.py](scripts/cost_baseline.py) → [resources/eval/cost_baseline.md](resources/eval/cost_baseline.md) | |
| **B3 Cache tầng 1: Exact** | ✅ | `ExactCache`, `make_cache_key`, `llm_cache_scope` ([infra/cache/exact.py](src/backend/infra/cache/exact.py)); dùng trong `chat()`/`chat_parsed()` ([completion.py](src/backend/infra/llm/completion.py)) | Key = prompt + version + model + câu hỏi chuẩn hoá |
| **B3 Cache tầng 2: Semantic** | ✅ | [infra/cache/semantic.py](src/backend/infra/cache/semantic.py); benchmark [scripts/cache_benchmark.py](scripts/cache_benchmark.py) với [replay_faq.yaml](resources/eval/replay_faq.yaml) → [cache_benchmark.md](resources/eval/cache_benchmark.md) | ⚠️ `chat_stream` (luồng SSE) chưa đi qua cache |
| **B3 Model routing & cascading** | ✅ | `resolve_model_chain`, `call_with_model_cascade` ([infra/llm/providers.py](src/backend/infra/llm/providers.py)); `select_answer_model` (light/heavy) | |
| **B3 Cost governance (budget)** | ✅ | `check_budget_or_raise`, `BudgetExceededError`, `is_over_alert_threshold` ([tracker.py](src/backend/infra/cost/tracker.py)); `cost_daily_limit_usd`, `cost_alert_threshold_usd` trong config; [scripts/drill_cost_alert.py](scripts/drill_cost_alert.py) | |
| **B4 Docker multi-stage, non-root (gosu)** | ✅ | [src/backend/Dockerfile](src/backend/Dockerfile) (`builder` → `runner`), [src/backend/docker-entrypoint.sh](src/backend/docker-entrypoint.sh); [src/frontend/Dockerfile](src/frontend/Dockerfile); [docker-compose.yml](docker-compose.yml) | |
| **B4 Self-hosted serving vLLM/TGI (OpenAI-compatible)** | 🟡 | Hỗ trợ backend `vllm` qua `base_url` ([backends.py](src/backend/infra/llm/backends.py)) | Chưa có cấu hình GPU/vLLM trong compose |
| **B4 FastAPI patterns: SSE streaming** | ✅ | `stream_chat_generator(_async)`, `/chat/stream` ([api/routers/chat.py](src/backend/api/routers/chat.py)); header `X-Accel-Buffering: no` | Hủy pipeline khi client ngắt (`StreamCancelledError` trong [graph/chat.py](src/backend/graph/chat.py)) |
| **B4 FastAPI: giới hạn request LLM đồng thời** | 🟡 | `llm_semaphore_slot` ([infra/llm/semaphore.py](src/backend/infra/llm/semaphore.py)) trên `chat` / `chat_parsed` | `chat_stream` chưa giữ slot; semaphore là `threading`, chưa `asyncio` |
| **B4 Health check** | ✅ | `GET /health` ([api/main.py](src/backend/api/main.py)) | |
| **B5 Production patterns: Nginx reverse proxy** | ✅ | [src/deploy/nginx-portfolio-watch.conf](src/deploy/nginx-portfolio-watch.conf), [src/frontend/nginx.conf](src/frontend/nginx.conf) | |
| **B5 Secrets management** | 🟡 | Tách `.env` (secret) khỏi [config.yaml](resources/configs/config.yaml); [shared/secrets.py](src/backend/shared/secrets.py), [shared/settings.py](src/backend/shared/settings.py) | Không dùng GCP Secret Manager |
| **B5 Public URL / smoke test** | ✅ | [scripts/start_ngrok_demo.py](scripts/start_ngrok_demo.py), [src/deploy/smoke.py](src/deploy/smoke.py) | Thay cho Compute Engine |
| **B6 CI (lint + test nhanh)** | ✅ | [.github/workflows/ci.yml](.github/workflows/ci.yml); [.pre-commit-config.yaml](.pre-commit-config.yaml); test mock offline: [tests/conftest.py](tests/conftest.py) | |
| **B6 CD + rollback last-known-good** | ✅ | [.github/workflows/cd.yml](.github/workflows/cd.yml) (build → health → smoke → lưu LKG SHA → rollback khi lỗi) | |
| **B7 Tracing production + sampling** | 🟡 | `should_sample` (100% lỗi/guardrail/chậm, 5% bình thường), `redact_pii` ([tracing.py](src/backend/infra/monitoring/tracing.py)) | Chưa bỏ trace khi `cache_hit`; chưa tín hiệu copied/regenerated/abandoned |
| **B7 Token & cost analytics / dashboard** | ✅ | [scripts/cost_dashboard.py](scripts/cost_dashboard.py) → [resources/eval/cost_dashboard.md](resources/eval/cost_dashboard.md) | |
| **B7 Guardrails at scale** | ✅ | Input + output guardrail ở trên; `guardrail_refusal_node` ([graph/chat.py](src/backend/graph/chat.py)) | |
| **B7 Incident response & fallback provider** | ✅ | `call_with_backend_fallback` openai → ollama → vllm ([providers.py](src/backend/infra/llm/providers.py)); heuristic fallback khi mọi provider lỗi (`run_answer_composer`); playbook: [resources/docs/incident-playbook-*.md](resources/docs/); diễn tập: [scripts/drill_fallback_provider.py](scripts/drill_fallback_provider.py) | |
| **B8 Capstone: pipeline tích hợp end-to-end** | ✅ | `answer_question` ([application/answer_question.py](src/backend/application/answer_question.py)) → `run_chat_graph`; sơ đồ: [resources/docs/m3-production-pipeline.md](resources/docs/m3-production-pipeline.md) | |

---

## Kỹ thuật bổ sung (không nằm trong Handbook nhưng có trong code)

| Kỹ thuật | Vị trí |
|---|---|
| Ports & Adapters (Clean Architecture), DI qua `AppDeps` | [domain/ports.py](src/backend/domain/ports.py), [api/deps.py](src/backend/api/deps.py) |
| "Brain" Protocol: LLM cho production, Heuristic cho test/offline | Mọi `agents/*/nodes.py` |
| Chỉ báo kỹ thuật RSI / SMA / Golden-Death Cross | [domain/indicators.py](src/backend/domain/indicators.py) |
| Biểu đồ nến/so sánh bằng Matplotlib | [agents/chart_agent.py](src/backend/agents/chart_agent.py) |
| Quét định kỳ (cron) | [infra/scheduler/cron.py](src/backend/infra/scheduler/cron.py) |
| Multi-tenant portfolio (P&L, NAV theo `user_id`) | [application/portfolio_service.py](src/backend/application/portfolio_service.py), [agents/portfolio_watch_agent/](src/backend/agents/portfolio_watch_agent/) |
| Spec-Driven Development | [specs/](specs/) |

---

## Tổng kết

- **Đã dùng tốt:** Structured output, streaming, backoff + xoay vòng key, LangGraph StateGraph, Supervisor multi-agent, ReAct, query rewrite/decomposition, memory ngắn hạn và dài hạn, guardrails 2 lớp, cache 2 tầng, chuỗi model/backend dự phòng, Prompt Registry + A/B + lint, golden eval + LLM judge + eval gate, cost governance, tracing có sampling và che PII, Docker, CI/CD có rollback.
- **Dùng một phần:** Function calling (có hàm nhưng không dùng), RAG (chỉ grounding từ tool, không có tài liệu), Self-RAG (chỉ có vòng tự sửa), context compression, vLLM serving, secrets manager.
- **Chưa dùng:** Fine-tuning LoRA/QLoRA, metric RAGAS/BLEU/ROUGE, MCP, LangGraph checkpointer/`interrupt`, model routing bằng embedding/classifier.
- **Lưu ý:** `Modelfile` vẫn là persona pháp lý cũ. `chat_stream` chưa đi qua cache 2 tầng và chưa dùng cascade model; nó có fallback backend. `chat()` và `chat_parsed()` đã có cache, semaphore, và cascade. Secret Manager trong `shared/secrets.py` còn stub.
