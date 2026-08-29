# Lộ trình build từng AI Agent — vn-stock-swarm/ dựa trên llm-engineer-demo/

## Bối cảnh

`vn-stock-swarm/` hiện có 2 tầng hoàn chỉnh nhưng **chưa dùng LLM thật**:

- **Tầng Swarm crawl-time** (Sơ đồ 1&2 — xong, giữ nguyên): 5 loại agent crawl
  (`ScoutAgent`/`RenderAgent`/`DocumentAgent`/`ApiAgent`/`StealthAgent`) +
  `ContentRouter` + `SinkRouter`. Không đụng tới ở lộ trình này.
- **Tầng Hierarchical Query Coordinator** (Sơ đồ 3d — xong về mặt luồng, nhưng
  "não" của từng agent chỉ là code Python thuần/heuristic từ khoá):
  `PriceAgent`, `NewsAgent`, `EvalAgent`, `DBAgent`, `SynthesisAgent`, điều phối
  bởi `QueryCoordinator` theo 2 đợt cố định + HITL 2-step
  (`POST /ask` → `POST /approve`).

`llm-engineer-demo/` (giờ nằm cùng cấp, thư mục `llm-engineer-demo/`) là codebase
thực hành 2 module LLM Engineer, đã code sẵn **từng viên gạch** cần để nâng cấp
5 agent trên từ heuristic → LLM thật: gọi LLM native SDK, RAG, structured
output/tool-calling, LLM-as-Judge, multi-agent orchestration, guardrails, eval,
tối ưu chi phí. Lộ trình dưới đây build **từng agent một**, mỗi agent tái dùng
đúng 1-2 pattern cụ thể từ `llm-engineer-demo/`, theo thứ tự độ phức tạp tăng
dần và theo đúng phụ thuộc dữ liệu đã có trong `QueryCoordinator`
(`vn-stock-swarm/src/vn_stock_swarm/query/coordinator.py`).

**Triết lý giữ nguyên từ cả 2 project:** native SDK trước, không kéo framework
nặng khi chưa cần. `QueryCoordinator` đã tự viết orchestration 2-đợt bằng
`asyncio.gather` thuần — **không bắt buộc chuyển sang LangGraph**. Tham khảo
kiến trúc `hierarchical.py` (Supervisor + state cô lập), nhưng chỉ thay "bộ não"
bên trong mỗi agent bằng LLM call thật, giữ nguyên khung điều phối hiện có.

## Bản đồ tham chiếu nhanh — agent nào dùng module nào

| Agent (vn-stock-swarm) | Vai trò hiện tại (heuristic) | Module tham chiếu chính trong llm-engineer-demo/ | Pattern áp dụng |
|---|---|---|---|
| `EvalAgent` | Khớp từ khoá 3 lớp cố định | `app/eval/judge.py` | LLM-as-Judge, rubric tuyệt đối, `chat_parsed` |
| `PriceAgent` | Tính % thuần Python | `app/prompts/templates.py`, `app/schemas/domain.py` | `chat_parsed` + Pydantic schema, không cần RAG |
| `NewsAgent` | Đọc tin thô từ SinkStore | `app/retrieval/` (loader/chunking/retriever), `app/llm/completion.chat` | Tóm tắt bằng `chat()`; RAG đầy đủ là tùy chọn nâng cao |
| `DBAgent` | Soạn `PendingWrite` cứng | `app/tools/registry.py`, `app/agent_m2/tools.py` | Function calling / structured tool-call cho truy vấn+ghi |
| `SynthesisAgent` | Ghép chuỗi string | `app/agent_m2/multi_agent/hierarchical.py`, `collaborative.py` | Tổng hợp nhiều báo cáo bằng LLM, có thể thêm vòng phản biện |
| `QueryCoordinator` (hub) | Điều phối 2 đợt | `app/guardrails/checks.py`, `app/monitoring/tracing.py` | Input guardrail trước khi route; tracing toàn luồng |

**Thứ tự build đề xuất:** EvalAgent → PriceAgent → NewsAgent → DBAgent →
SynthesisAgent → (tùy chọn) Guardrails + Tracing ở tầng Coordinator. Lý do thứ
tự: EvalAgent là pattern đơn giản nhất và độc lập nhất (input đã có sẵn từ
Price+News, không cần gọi Swarm/DB) — làm trước để dựng xong "lớp gọi LLM dùng
chung" cho vn-stock-swarm mà không phải lo phần crawl/ghi DB phức tạp hơn.

## Việc dùng chung cho MỌI agent — làm 1 lần trước tiên

Trước khi build agent đầu tiên, dựng lớp hạ tầng LLM tối thiểu trong
`vn-stock-swarm/src/vn_stock_swarm/llm/` (thư mục mới), mô phỏng đúng
`llm-engineer-demo/app/llm/`:

- `client.py` — factory OpenAI client (native SDK, đọc `OPENAI_API_KEY` từ
  `Settings` đã có trong `config.py`). Không cần đa backend (Ollama/vLLM) ngay
  — có thể thêm sau nếu muốn chạy local giống Module I Buổi 2.
- `completion.py` — chỉ cần 2 hàm trước: `chat()` (text thuần) và
  `chat_parsed()` (structured output Pydantic) — đủ cho cả 5 agent, không cần
  `chat_stream()`/`chat_with_tools()` ngay từ đầu.
- `params.py` — `GenerationParams` tối giản (model, temperature, max_tokens).

Không cần `resilience.py` (retry/backoff/key rotation) ngay ở bản đầu — thêm
khi đã chạy ổn với 1 agent, tránh over-engineer trước khi biết pattern có hoạt
động đúng không.

`Settings` (`config.py`) cần thêm field mới: `openai_api_key`, `llm_model`
(mặc định `gpt-4o-mini` — rẻ, đủ cho tác vụ ngắn của các agent này).

## Bước 1 — EvalAgent: heuristic từ khoá → LLM-as-Judge

**File:** `vn-stock-swarm/src/vn_stock_swarm/query/agents/eval_agent.py`

Thay `_classify()` (khớp từ khoá cứng `_NEGATIVE_KEYWORDS`/`_POSITIVE_KEYWORDS`)
bằng 1 lời gọi LLM chấm sentiment + đủ-bằng-chứng + khớp-giá-tin, dùng đúng
pattern `judge_answer()` trong `llm-engineer-demo/app/eval/judge.py`:

1. Định nghĩa `Pydantic` schema mới (giống `JudgeScore`) — ví dụ
   `NewsSentimentJudgment(sentiment: Literal["negative","positive","neutral"],
   confidence: float, reasoning: str)`.
2. Viết system prompt rubric tuyệt đối (không so sánh nhiều tin với nhau) —
   tránh **verbosity bias** (tin dài không tự nhiên "nghiêm trọng hơn") và
   **style bias**, đúng 2 loại bias liệt kê trong docstring `judge.py`.
3. Gọi `completion.chat_parsed(messages, NewsSentimentJudgment, params)` cho
   từng tin trong `NewsReport.articles` — thay hàm `_classify()` thuần Python.
4. Giữ nguyên toàn bộ phần còn lại của `EvalAgent` (`has_enough_evidence`,
   `_price_matches_news` — logic đối chiếu chiều giá vẫn có thể giữ thuần
   Python, không cần LLM cho phép so sánh số học đơn giản).

**Vì sao làm trước:** input (`PriceReport` + `NewsReport`) đã có sẵn khi
`EvalAgent` chạy (đợt 2a) — không phụ thuộc Swarm/DB đang chạy thật, nên viết
test dễ nhất (mock `chat_parsed`, không cần fakeredis phức tạp).

**Test:** `tests/test_query_agents/test_eval_agent.py` — mock
`completion.chat_parsed` trả về `NewsSentimentJudgment` cố định (giống cách
`test_agent_m2_multi_agent.py` mock `base_llm()` bằng `FakeLLM`), giữ nguyên
các case cũ (3 lớp sentiment, đủ bằng chứng, khớp giá) nhưng qua đường LLM giả lập.

## Bước 2 — PriceAgent: thêm khả năng giải thích bằng ngôn ngữ tự nhiên

**File:** `vn-stock-swarm/src/vn_stock_swarm/query/agents/price_agent.py`

`PriceAgent` hiện tại chỉ tính `pct_change` bằng số học — **không cần LLM cho
phần tính toán này** (giữ nguyên, LLM không giỏi hơn code thuần ở việc trừ 2 số).
Việc LLM hoá ở đây là thêm 1 bước MỚI: sinh `detail` (mô tả 1 dòng) bằng LLM
thay vì f-string cứng, để câu trả lời tự nhiên hơn và có thể diễn giải theo ngữ
cảnh (vd "giảm nhẹ trong biên độ bình thường" vs "giảm mạnh bất thường").

1. Thêm schema Pydantic `PriceNarrative(summary: str, severity: Literal["nhẹ",
   "trung bình","mạnh"])`, mẫu theo `LegalAnswer` trong `app/schemas/domain.py`.
2. Prompt đơn giản, dùng `chat_parsed` — input là `pct_change` + lịch sử giá,
   KHÔNG cần RAG (đây là dữ liệu số có cấu trúc, không phải tài liệu tự do).
3. Đây là bước "tập dùng `chat_parsed` lần 2" sau EvalAgent, củng cố pattern
   trước khi sang NewsAgent (phức tạp hơn vì có văn bản dài).

**Vì sao làm thứ 2:** đơn giản hơn NewsAgent (không cần tóm tắt văn bản dài),
nhưng khác EvalAgent ở việc dùng dữ liệu số + lịch sử thay vì văn bản — bài tập
tốt để quen dần với việc thiết kế schema Pydantic khác nhau cho từng agent.

**Test:** thêm case mock `chat_parsed` trả `PriceNarrative`, verify `detail`
trong `PriceReport` giờ đến từ LLM thay vì f-string.

## Bước 3 — NewsAgent: tóm tắt tin bằng LLM (tùy chọn: RAG đầy đủ)

**File:** `vn-stock-swarm/src/vn_stock_swarm/query/agents/news_agent.py`

`NewsAgent` hiện đọc tin thô (title/url/ts) từ SinkStore, không xử lý gì thêm
— đúng thiết kế "chỉ search, không đánh giá". Nâng cấp LLM ở đây là THÊM 1
bước tóm tắt, không đổi trách nhiệm gốc (tóm tắt ≠ đánh giá sentiment, vẫn
thuộc EvalAgent):

**Phương án A (đơn giản, làm trước):** dùng `completion.chat()` để tóm tắt
danh sách title thành 1 đoạn ngắn "điểm tin trong ngày" — không cần RAG vì input
đã có sẵn (title từ SinkStore), không phải tìm kiếm trong kho tài liệu lớn.

**Phương án B (nâng cao, tùy chọn sau):** nếu muốn NewsAgent tóm tắt cả NỘI
DUNG bài báo (không chỉ title) từ `extracted_text` mà `ContentRouter` đã lưu,
cần dựng RAG-lite theo `app/retrieval/`:
- `chunking.py` — chia nội dung bài dài thành đoạn.
- `embeddings.py` + `vectorstore.py` (Qdrant, dùng lại
  `llm-engineer-demo/docker-compose.yml` — service Qdrant duy nhất, port 6333)
  — chỉ cần nếu số lượng tin/mã đủ lớn để cần semantic search thay vì đọc hết.
- Nếu chỉ vài tin/mã/lần hỏi (thực tế hiện tại — demo 4 mã), **Phương án A đủ
  dùng**, không cần vectorstore — tránh over-engineer.

**Vì sao làm thứ 3:** phức tạp hơn Bước 1-2 vì xử lý văn bản tự do (title
tiếng Việt đa dạng) thay vì số liệu có cấu trúc; quyết định RAG hay không cũng
là bài học thực tế đúng tinh thần Buổi 4-5 Module I ("khi nào cần RAG thật").

**Test:** mock `completion.chat()` trả về 1 đoạn tóm tắt cố định, verify
`NewsReport` có thêm field `summary: str` mới.

## Bước 4 — DBAgent: structured tool-call cho truy vấn + ghi

**File:** `vn-stock-swarm/src/vn_stock_swarm/query/agents/db_agent.py`

Đây là agent phức tạp nhất về mặt an toàn (đã có HITL). Mục tiêu: để LLM tự
quyết định/soạn câu truy vấn thay vì code cứng `prepare_pending_writes()`,
nhưng **HITL giữ nguyên 100% không đổi** — LLM chỉ được phép ĐỀ XUẤT, không
bao giờ tự động commit (đúng nguyên tắc "tool có side-effect luôn dừng chờ
duyệt" trong `README.module2.md` Buổi 2).

1. Định nghĩa tool theo `app/tools/registry.py` (JSON schema + `DISPATCH`):
   - `read_price_history(symbol, limit)` — tool ĐỌC, không cần duyệt.
   - `propose_news_write(symbol, title, url)` — tool GHI, luôn tạo
     `PendingWrite`, KHÔNG commit trực tiếp (dispatch chỉ soạn, không gọi
     `SinkStore.save_news`).
2. Dùng `completion.chat_with_tools()` để LLM chọn tool + tham số dựa trên
   ngữ cảnh câu hỏi, thay vì luôn chạy `prepare_pending_writes()` cứng cho mọi
   tin NewsAgent tìm thấy — LLM có thể quyết định tin nào "đáng ghi" (vd bỏ
   qua tin trùng lặp nội dung dù khác URL).
3. Nếu muốn nâng cao hơn (không bắt buộc): áp dụng `idempotency_key` pattern
   từ `app/agent_m2/tools.py` (Buổi 4) cho `propose_news_write` — tránh tạo
   nhiều `PendingWrite` trùng nếu LLM gọi tool 2 lần cho cùng 1 tin.

**Vì sao làm thứ 4:** cần cả 2 pattern trước đó ổn định (Eval dùng
`chat_parsed`, News có văn bản cần tóm tắt) trước khi thêm lớp phức tạp nhất —
tool-calling với ràng buộc an toàn (HITL) không được phá vỡ.

**Test:** mở rộng `tests/test_query_agents/test_db_agent.py` — mock
`chat_with_tools` trả `tool_calls` giả, verify `PendingWrite` vẫn được tạo
đúng qua dispatch, và **quan trọng nhất: verify không có đường nào LLM tự gọi
thẳng `SinkStore.save_news`/`promote_pending_news`** (giữ đúng bất biến HITL).

## Bước 5 — SynthesisAgent: tổng hợp nhiều báo cáo bằng LLM

**File:** `vn-stock-swarm/src/vn_stock_swarm/query/agents/synthesis_agent.py`

Thay việc ghép string thủ công (`" ".join(parts)`) bằng 1 lời gọi LLM tổng hợp
4 báo cáo (`PriceReport`, `NewsReport`, `EvalReport`, `DBReadResult`) thành câu
trả lời tự nhiên — đây là bước hưởng lợi trực tiếp từ 3 bước trước (giờ mỗi
input đã "giàu" hơn: có `PriceNarrative`, `summary` tin tức, `NewsSentimentJudgment`
thay vì chỉ số/string thô).

1. Dùng `completion.chat()` (không cần structured output — đây là câu trả lời
   tự do cho user, không phải dữ liệu máy đọc tiếp).
2. Prompt ghép 4 báo cáo thành context, yêu cầu LLM **CHỈ dùng dữ liệu đã cho**
   (đúng nguyên tắc groundedness trong `LEGAL_SYSTEM_PROMPT` — không tự bịa
   thêm nguyên nhân ngoài 4 báo cáo, giữ đúng docstring gốc của
   `SynthesisAgent`: "không tự đi lấy gì thêm, không tự chấm lại").
3. **Tùy chọn nâng cao:** áp dụng pattern `collaborative.py` (Planner⇄Critic)
   — thêm 1 vòng LLM tự phê bình câu trả lời vừa sinh trước khi trả về hub
   (`MAX_ROUNDS` nhỏ, vd 1-2 vòng) — hữu ích nếu muốn tăng chất lượng câu trả
   lời cuối, nhưng KHÔNG bắt buộc cho bản đầu.

**Vì sao làm cuối:** phụ thuộc dữ liệu từ cả 4 báo cáo trước — hưởng lợi tối
đa khi các bước 1-4 đã hoàn thành, và là nơi "gộp tất cả lại" nên hợp lý để
làm sau cùng, dễ demo trọn vẹn luồng.

**Test:** mock `completion.chat()` trả câu trả lời cố định, verify
`SynthesisResult.answer` đến từ LLM; giữ lại các test cũ về nội dung câu trả
lời (đề cập chiều giá, cảnh báo lệch giá/tin) bằng cách assert trên input
prompt gửi cho LLM thay vì trên string ghép cứng.

## Bước 6 (tùy chọn, sau khi cả 5 agent chạy LLM thật) — hạ tầng chất lượng

Không phải "agent" mới, nhưng đáng làm sau khi 5 agent trên ổn định:

- **Guardrails** (`app/guardrails/checks.py`) — thêm `check_input()` vào đầu
  `QueryCoordinator.ask()`, chặn prompt injection trong câu hỏi user trước khi
  route xuống 5 agent. Áp dụng ở ĐÚNG 1 chỗ (hub), không lặp lại ở từng agent.
- **Monitoring** (`app/monitoring/tracing.py`) — bọc `QueryCoordinator.ask()`
  bằng `trace_answer()`, và mỗi lời gọi LLM trong 5 agent bằng `trace_step()`
  (nested span) — cho thấy toàn bộ luồng 2 đợt trên LangFuse, đúng mô hình
  Buổi 5 Module I/II. Mặc định tắt (`MONITORING_ENABLED=false`), không bắt
  buộc cài LangFuse để chạy phần còn lại.
- **Eval cho cả luồng** (`app/eval/judge.py` + ý tưởng
  `app/agent_m2/eval.py::evaluate_trajectory`) — viết 1 script tương tự
  `scripts/eval_demo.py`, chấm câu trả lời cuối của `QueryCoordinator` trên 1
  bộ câu hỏi mẫu (HPG/VNM/FPT/VCB), dùng `judge_answer()` để có eval gate
  PASS/FAIL trước khi coi 1 agent là "xong".
- **Optimization** (`app/optimization/`) — chỉ cần khi đã thấy chi phí/latency
  là vấn đề thật: `prompt_cache.py` (format prompt để tận dụng cache OpenAI —
  áp dụng dễ nhất, không đổi logic), `routing.py` (route câu hỏi đơn giản
  sang model rẻ hơn cho PriceAgent/EvalAgent, câu hỏi phức tạp sang model mạnh
  hơn cho SynthesisAgent).

## Nguyên tắc xuyên suốt khi build từng agent

1. **Không đổi interface public của agent** (tên class, method `run()`, shape
   dataclass trả về) trừ khi thật sự cần thêm field mới (vd `PriceReport.detail`
   giờ từ LLM thay vì f-string — field vẫn tên `detail`, kiểu vẫn `str`) — để
   `QueryCoordinator` và test hiện có không phải viết lại toàn bộ.
2. **Mock LLM trong test, không gọi API thật** — đúng triết lý
   `llm-engineer-demo` (`pytest` không cần key), giữ CI nhanh và không tốn phí.
3. **HITL của DBAgent là bất biến tuyệt đối** — không bước nào ở trên được
   phép làm LLM tự ý commit ghi dữ liệu mà bỏ qua `POST /approve`.
4. **Giữ style code + docstring tiếng Việt** đã thiết lập trong
   `vn-stock-swarm/` (module-level docstring giải thích pattern + lý do thiết
   kế, không chỉ mô tả tham số) — áp dụng cho mọi file mới ở `llm/`.
5. **1 agent xong = có test xanh + 1 lần gọi thử qua `/ask` thật** (giống cách
   đã verify HITL bằng dữ liệu crawl thật trước đó) trước khi chuyển sang agent
   kế tiếp — không dồn nhiều agent rồi mới test chung.
