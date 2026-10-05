# Phase 3a Quality Report — Golden dataset

**Ngày báo cáo:** 2026-09-18  
**Đối chiếu:** `specs/product-spec.md` (AC1–3), `specs/test-plan.md` §1,  
`specs/implementation-plan.md` Phase 3a  
**Dataset:** `specs/eval/golden_dataset.yaml` (30 case, 18/6/3/3)  
**Runner:** `python scripts/run_eval.py --run --skip-judge`  
(+ task_success / trajectory; không `--skip-agent-eval`)

---

## 1. Số case pass

| Slice | Passed | Total | Rate |
|---|---:|---:|---:|
| lookup | 18 | 18 | 100% |
| comparison | 6 | 6 | 100% |
| out_of_scope | 3 | 3 | 100% |
| injection | 3 | 3 | 100% |
| **Tổng** | **30** | **30** | **100%** |

- **Injection gate:** 3/3 (100%, không tolerance) — đạt AC2.
- **Fail list:** (không).
- **Pass từng case (id):**  
  `lookup_01`…`lookup_18`; `comparison_01`…`comparison_06`;  
  `out_of_scope_01`…`03`; `injection_01`…`03` — **tất cả pass**.
- **LLM-judge:** chưa bật trên full run này (`--skip-judge`); giữ cho
  regression / lần chạy tốn token sau.

Cách tái hiện (tránh rate-limit vnstock guest: cách ~5–6s mỗi case):

```bash
unset SSL_CERT_FILE   # nếu đường dẫn cert Windows lỗi
python scripts/run_eval.py --run --case-id lookup_01 --skip-judge
# hoặc full:
python scripts/run_eval.py --run --skip-judge
```

Mốc regression trước vòng debug: `specs/eval/baseline_debug.json` (30/30
rule-only). Sau Phase 3a, điểm tổng vẫn 1.0 với scorer đã nâng
(task_success).

---

## 2. Thay đổi agent / prompt / tool (Quality Loop)

Không nới scorer / không sửa `expected` chỉ để pass.

| # | Case / gap | Thay đổi | File chính |
|---|---|---|---|
| 1 | `lookup_15` — `news_agent items=0` | CafeF URL → `cafef.vn/du-lieu/...`; bỏ lọc `query` chữ trên title | `infra/market_data/news_source.py` |
| 2 | comparison đa mã chỉ 1 ticker | `RewrittenQuestion.symbols`; extract đa mã; fetch giá/tin từng mã; evidence/composer gộp | `domain/agents/supervisor.py`, `application/answer_question.py`, `domain/agents/answer_composer.py` |
| 3 | So sánh / biến động → sai intent | Hint «biến động / mạnh hơn / đối chiếu»; đa mã → `explain` | `supervisor.py`, `prompts/rewrite_question/v1.yaml` |
| 4 | «tin tức» → ticker giả `TIN` | Thêm stopword `TIN` (+ vài từ VN 3 chữ) | `supervisor.py` |
| 5 | Composer thiếu nhắc đủ mã | Prompt: nêu đủ từng mã khi so sánh | `prompts/answer_compose/v1.yaml` |
| 6 | Eval memory lệch symbol giữa case | `user_id=eval-{case_id}` mỗi case | `scripts/run_eval.py` |

**Phase 3c đã đóng nhờ gap trên:** Supervisor routing câu hỏi đa mã.

**Backlog 3c còn mở:** (trống — evidence giá, rewrite đại từ, guardrail
grounding đã đóng 2026-09-18). Thêm task khi debug case fail.

---

## 3. Đối chiếu acceptance (rút gọn)

| Tiêu chí | Kết quả |
|---|---|
| AC1 — báo cáo + toàn bộ case pass (scorer đã chốt) | **Đạt** trên rule + task_success; báo cáo này |
| AC2 — injection 100% | **Đạt** |
| AC3 — case fail có ghi chú + backlog | **Đạt** (mục 2 + change-log + 3c) |
| test-plan — report theo slice | **Đạt** (bảng mục 1) |

**Còn thiếu ngoài báo cáo này:** LLM-judge full 30; Backend/FE/Langfuse
(Phase 3b+).

---

## 4. Tài liệu liên quan

- Nhật ký chi tiết: `specs/change-log.md` (mục 2026-09-18 Phase 3a).
- Baseline debug: `specs/eval/baseline_debug.json`.
- Agents: `specs/agents.md`.
