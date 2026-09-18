# Test Plan — Quality Loop + Split FE/BE/AI

Nguyên tắc: **chất lượng trước**, tách deploy sau. Mỗi case golden là một
đơn vị debug. Không nới scorer để đạt pass rate giả.

## 1. Eval & golden dataset

### Nguồn dữ liệu

- File: `specs/eval/golden_dataset.yaml` (30 case, slice 18/6/3/3).
- Runner hiện có: `scripts/run_eval.py`.
- Nâng cấp (Phase 1 setup): thêm task_success + trajectory theo
  `llm-engineer-demo/app/agent_pr/eval.py`.

### Rule-based (giữ)

- `must_include` / `must_not_include` trên output cuối.
- Injection: không được lộ hành vi bị thao túng; slice injection **pass
  100%**, không tolerance.

### LLM-judge (giữ cho lookup / comparison)

- Tiêu chí: correctness / completeness / grounding (1–5).
- Pass khi overall ≥ ngưỡng đã chốt (hiện tại 3.0) **và** rule-based pass.

### Task success (mới — port ý tưởng demo)

- Input: câu hỏi + câu trả lời cuối (+ criteria từ `expected` nếu có).
- Output: `success: bool`, `score: 0–1`, `reasoning`.
- Pass case (lookup/comparison): `success == true` (hoặc score ≥ 0.7 nếu
  đổi sang ngưỡng liên tục — chốt một lần trong change-log Phase 1).

### Trajectory (mới — chủ yếu để chẩn đoán)

- Input: chuỗi bước agent/tool thật từ hệ thống.
- Tiêu chí 1–5: efficiency, logical_order, tool_correctness, recovery.
- MVP: **không chặn pass case** nếu task_success + rule (+ judge) đã pass,
  nhưng overall trajectory < 3.0 → ghi **cảnh báo** và ưu tiên sửa
  multi-agent trước khi đóng Phase 3a (golden).
- Sau khi ổn định: có thể nâng trajectory thành gate cứng (ghi rõ khi đổi).

### Quy trình test từng case

```text
python scripts/run_eval.py --case-id lookup_01
# hoặc: python scripts/run_eval.py --run --case-id lookup_01 --skip-judge
```

Pass lookup/comparison: rule + (judge nếu bật) + `task_success.success == true`.
Trajectory overall < 3.0 → cảnh báo, không fail case (MVP).

Checklist khi fail:

1. Đọc output thật + reasoning scorer.
2. Xem trajectory / Langfuse (nếu có) — sai bước nào.
3. Sửa agent/prompt/tool.
4. Chạy lại **đúng case đó** đến khi pass.
5. Cập nhật change-log (ngắn) + Phase 3c nếu cần task mới.
6. Mới chuyển case tiếp theo.

### Regression

- Sau Phase 3a (golden pass) và sau Phase 5/7: full 30 case.
- Điểm tổng không giảm quá `REGRESSION_TOLERANCE` (0.05) so với baseline
  lúc 30/30 (hoặc so với baseline_debug nếu chưa đạt 30).
- Injection luôn 100%.

## 2. Unit / tích hợp AI (giữ từ MVP, chạy khi đụng agent)

- Price / News / Classifier / Eval / Synthesis / Supervisor / Guardrail /
  HITL — theo checklist cũ trong change-log MVP; khi sửa agent liên quan
  thì chạy lại test tương ứng:
  `pytest` (env `dong312`).

## 3. Tách Frontend / Backend / AI

### Contract

- Backend → AI: chat/scan trả JSON có `steps: [{id, name, status, detail?}]`
  và kết quả cuối.
- Frontend → Backend: không gọi thẳng AI URL trong code production path.

### Kiểm thử thủ công

1. Chỉ bật AI → health OK; Backend down → Frontend báo lỗi rõ.
2. AI + Backend → `curl` chat qua Backend nhận answer + steps.
3. Cả 3 process → UI chat hiện timeline bước, rồi câu trả lời.
4. Tắt AI giữa chừng → Frontend/Backend không treo vô hạn (timeout/error).

### Stream bước

- Mỗi bước chuyển trạng thái hiển thị trên UI (ít nhất: start + done).
- Thứ tự bước khớp tương đối với trace Langfuse (cùng request).

## 4. Langfuse

- `MONITORING_ENABLED=false` → chat vẫn OK, không exception.
- `true` + key hợp lệ → 1 request chat tạo 1 trace; có span con theo agent.
- Sai key / host → log cảnh báo, không crash request (best-effort).
- Backend sinh `request_id` → AI nhận (body/`X-Request-Id`) → metadata
  Langfuse có cùng `request_id` (tìm trace theo id / câu hỏi).

## 5. Acceptance map (product-spec)

| Tiêu chí | Cách chứng minh |
|---|---|
| 30/30 golden (theo scorer đã chốt) | `run_eval` full + báo cáo |
| Injection 100% | slice report |
| Case fail có ghi chú + backlog | change-log + Phase 3c |
| 3 process riêng | README lệnh + thử tay |
| UI timeline bước | demo thủ công 1 câu hỏi |
| Langfuse trace | screenshot / link trace id trong báo cáo |
| Backend không import agents | grep / review cấu trúc `backend/` |
