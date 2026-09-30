# Incident Playbook: Hallucination Spike

## Triệu chứng

- `hallucination_rate` trong eval report > ngưỡng (mặc định 15%)
- User feedback báo số liệu sai ticker/giá không khớp tool output
- Judge `groundedness` fail tăng đột biến trên Langfuse dashboard

## Phát hiện nhanh

```bash
PYTHONPATH=src python scripts/cost_dashboard.py
PYTHONPATH=src python -m backend.eval.run --golden resources/eval/golden_v5.yaml --limit 10
```

Kiểm tra `specs/eval/runs/<latest>/report.json` → `metrics.hallucination_rate`.

## Nguyên nhân thường gặp

1. Prompt version mới (A/B variant B) kém grounded
2. Model cascade fallback sang model nhỏ hơn
3. Cache semantic trả về answer cũ không còn đúng giá
4. Tool timeout → model tự bịa số

## Hành động khẩn cấp (15 phút)

1. **Rollback prompt**: đặt `PROMPT_AB_ENABLED=false` hoặc `PROMPT_AB_SPLIT_PCT=0`
2. **Tắt semantic cache tạm**: `SEMANTIC_CACHE_ENABLED=false`
3. **Ép model chính**: `LLM_MODEL_CASCADE=` (để trống)
4. Chạy lại eval subset:

```bash
PYTHONPATH=src python scripts/run_golden_v5_eval_bundle.py --skip-agent-eval --limit 20
```

5. Nếu pass → deploy config; nếu fail → rollback git tag LKG (xem `incident-playbook-provider-outage.md`)

## Khắc phục dài hạn

- Thêm golden cases cho ticker bị hallucinate
- Tăng weight `groundedness` trong eval gate
- Review HITL feedback → export golden draft
- Bật lại A/B với split 10% trước khi mở rộng

## Escalation

- Hallucination > 30% sau rollback → page on-call, tắt `/chat` production (feature flag)
