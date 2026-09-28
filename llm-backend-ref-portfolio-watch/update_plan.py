import os

with open("specs/implementation-plan.md", "r", encoding="utf-8") as f:
    impl_plan = f.read()

impl_plan = impl_plan.replace(
    "- [ ] Mở rộng `infra/monitoring/tracing.py`", "- [x] Mở rộng `infra/monitoring/tracing.py`"
).replace(
    "  - [ ] `should_sample()`: 100% lỗi/guardrail/chậm, ~5% bình thường", "  - [x] `should_sample()`: 100% lỗi/guardrail/chậm, ~5% bình thường"
).replace(
    "  - [ ] Spans: guardrail, rewrite, supervisor, price, news, chart, composer", "  - [x] Spans: guardrail, rewrite, supervisor, price, news, chart, composer"
).replace(
    "- [ ] Redact PII (SĐT, email) trước export trace", "- [x] Redact PII (SĐT, email) trước export trace"
).replace(
    "- [ ] Script `scripts/cost_dashboard.py` — cost, p95, cache hit rate", "- [x] Script `scripts/cost_dashboard.py` — cost, p95, cache hit rate"
).replace(
    "- [ ] Viết `resources/docs/incident-playbook-cost-spike.md`", "- [x] Viết `resources/docs/incident-playbook-cost-spike.md`"
).replace(
    "- [ ] Viết `resources/docs/incident-playbook-jailbreak.md`", "- [x] Viết `resources/docs/incident-playbook-jailbreak.md`"
).replace(
    "- [ ] Diễn tập 1 incident — ghi log vào `change-log.md`", "- [x] Diễn tập 1 incident — ghi log vào `change-log.md`"
).replace(
    "| 13 | Observability + playbook | B7 | `[ ]` |", "| 13 | Observability + playbook | B7 | `[x]` |"
)

with open("specs/implementation-plan.md", "w", encoding="utf-8") as f:
    f.write(impl_plan)
