# agent_pr — Prompt Registry (LLMOps Module III, Bài 6)

Áp dụng hands-on "Prompt Registry cho Vietnamese RAG assistant" (Module III,
Phần 6 của `LLMOps Prompt Management.pdf`) vào `app/agent_pr` — swarm cổ
phiếu VN (`price_agent` / `news_agent` / `db_agent` / `eval_agent` +
supervisor). Đây là tài liệu sống: **cập nhật file này mỗi khi thêm/sửa
prompt hoặc đổi hành vi registry.**

## Vì sao cần refactor này

Trước đây 4 system prompt là hằng số hardcode giữa logic điều phối:

- `_REWRITE_SYSTEM`, `_SUPERVISOR_SYSTEM`, `_FINAL_ANSWER_SYSTEM` trong
  `app/agent_pr/supervisor_agent/nodes.py`
- `_SENTIMENT_SYSTEM` trong `app/agent_pr/eval_agent/nodes.py`

Đúng 6 hệ quả liệt kê trong slide "Prompt không được Quản lý": không version,
không đổi được mà không sửa code, không A/B test được, không tách được
người sửa (PM/prompt-engineer phải đụng vào `nodes.py`).

Refactor này **không đổi hành vi hệ thống** (production vẫn dùng đúng nội
dung prompt cũ ở v1) — chỉ di chuyển nơi prompt sống + thêm khả năng
version/A-B, đúng tinh thần "đây chính là refactor, không phải viết mới".

## Cấu trúc

```
app/agent_pr/
  prompt_registry/
    __init__.py          # PromptRegistry: get()/render(), interface tối thiểu
  prompts/
    rewrite_question/
      v1.yaml
      production.txt     # "1"
    supervisor_routing/
      v1.yaml
      v2.yaml             # ví dụ versioning: siết rule db_write, có changelog
      production.txt     # "1" — v2 CHƯA lên production, chỉ dùng qua A/B
    final_answer/
      v1.yaml
      production.txt
    eval_sentiment/
      v1.yaml
      production.txt
  scripts/
    compare_prompt_versions.py   # Bước 3: so output routing giữa 2 version
```

Git-based (không hosted): mỗi thay đổi = sửa YAML + PR, review qua diff bình
thường. Không có external dependency lúc runtime — không cần cơ chế
fallback cache (khác registry hosted, xem slide "Registry Hosted cần
Fallback").

## Metadata mỗi version (`v*.yaml`)

| Field | Ý nghĩa |
|---|---|
| `name`, `version` | Định danh — registry dùng để tìm file |
| `model` | Model prompt này được viết/tối ưu cho |
| `owner` | Người chịu trách nhiệm khi prompt có vấn đề |
| `changelog` | **Vì sao** đổi, không chỉ đổi gì |
| `status` | `production` / `deprecated` / `draft` — tham khảo, không code-enforce |
| `eval_score` | Điểm eval gần nhất (chưa nối với `app/eval` — để trống) |
| `template` | Nội dung prompt, biến dạng `$var` (`string.Template`, KHÔNG phải jinja2) |

## Dùng trong code

```python
from app.agent_pr.prompt_registry import registry

# Prompt tĩnh (không biến):
system = registry().get("rewrite_question", "production").template

# Prompt có biến — render() báo lỗi rõ nếu thiếu biến:
system = registry().render(
    "supervisor_routing", version="production", freshness_minutes="20"
)
```

`version` nhận: số cụ thể (`2`), `"production"` (đọc từ `production.txt`),
hoặc `"latest"` (version lớn nhất tồn tại).

## Đổi bản đang chạy (rollback)

Sửa `agent_pr/prompts/<name>/production.txt` (chỉ chứa 1 số) + PR — **không
sửa code gọi registry**. Rollback = revert PR đó, giống revert bất kỳ commit
code nào khác.

## A/B test: `supervisor_routing`

`pick_prompt_version()` (`app/agent_pr/supervisor_agent/nodes.py`) chọn
version theo **sticky hash của `user_id`** (cùng user luôn thấy cùng bản,
đúng slide "Traffic Splitting"):

```python
def pick_prompt_version(user_id, treatment_pct, treatment_version):
    if treatment_pct <= 0 or not user_id:
        return 1
    bucket = sha256(user_id) % 100
    return treatment_version if bucket < treatment_pct else 1
```

Cấu hình qua `.env` (`app/config.py`):

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `AGENT_PR_AB_TREATMENT_PCT` | `0` | % traffic (theo `user_id`) nhận bản treatment. `0` = tắt hẳn A/B |
| `AGENT_PR_AB_TREATMENT_VERSION` | `2` | Version dùng làm "treatment" |

Mỗi lượt routing được log (`supervisor_agent/nodes.py`, logger
`app.agent_pr.supervisor_agent.nodes`):

```
prompt_ab prompt=supervisor_routing version=2 user_id=alice
```

Đây là dữ liệu thô để đọc kết quả A/B sau này (primary metric + guardrail
metrics — chưa tự động hoá, xem "Việc CHƯA làm" bên dưới).

## Bước 3 — so sánh output giữa 2 version

```bash
python -m app.agent_pr.scripts.compare_prompt_versions
# hoặc chỉ định prompt/version khác:
python -m app.agent_pr.scripts.compare_prompt_versions --prompt supervisor_routing --v1 1 --v2 2
```

Chạy 5 tình huống mẫu (giá đơn mã, hỏi nguyên nhân, so sánh nhiều mã,
db_write, hỏi lại hội thoại) qua LLM thật với từng version, in
`next_agent` / `symbol` / `reasoning` cạnh nhau.

## Checklist hoàn thành (đối chiếu slide 38)

- [x] Không còn prompt hardcode trong `supervisor_agent/nodes.py` /
      `eval_agent/nodes.py`.
- [x] `supervisor_routing` có ≥ 2 version với changelog + metadata đầy đủ.
- [x] Đổi version production chỉ bằng sửa `production.txt`, không sửa code.
- [x] Rollback = revert 1 commit (revert PR sửa `production.txt`).
- [x] Có script so sánh output giữa 2 version
      (`scripts/compare_prompt_versions.py`).
- [x] A/B scaffold sticky theo `user_id` (`pick_prompt_version` +
      `AGENT_PR_AB_TREATMENT_PCT`).

## Việc CHƯA làm (ngoài phạm vi hands-on này)

- Chưa nối `eval_score` trong YAML với `app/eval` (Bài 2 — Eval Pipelines).
- Chưa có job đọc log `prompt_ab` để tính primary/guardrail metric tự động
  (Bài 6 Phần 5 "Đọc kết quả A/B Test") — hiện chỉ log thô.
- Chưa validate template trong CI (Bài 3 gợi ý `_required_vars()` + lint) —
  `render()` mới chỉ check lúc runtime.
- `rewrite_question` / `final_answer` / `eval_sentiment` mới có v1 (chưa có
  nhu cầu version 2 thật) — cấu trúc đã sẵn sàng khi cần.
- Prompt tóm tắt hội thoại trong `context.py::summarize_text` (dùng cho
  compact khi context vượt 40% window) **chưa** đưa vào registry — nằm ngoài
  4 prompt chính (rewrite/routing/final_answer/sentiment) mà slide minh hoạ,
  cân nhắc mở rộng registry cho nó khi cần version/A-B riêng.
