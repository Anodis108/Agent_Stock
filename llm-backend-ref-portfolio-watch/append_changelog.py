import datetime

new_log = f"""## {datetime.datetime.now().strftime("%Y-%m-%d")} — Phase 13 (M3-B7): Observability + Playbook [Hoàn Thành]

### Tóm tắt
- Cấu hình Langfuse Tracing (`src/backend/infra/monitoring/tracing.py`) với `should_sample` (head-based sampling ~5% normal requests, luôn trace lỗi/chậm).
- Sanitize PII (email, điện thoại) thông qua `redact_pii` trước khi tạo trace.
- Thêm script `scripts/cost_dashboard.py` tổng hợp báo cáo chi phí (USD/VND), cache hit rate và p95 latency.
- Viết 2 cuốn Playbook xử lý sự cố (Cost Spike & Jailbreak).
- Diễn tập mô phỏng (Drill) sự cố Cost Spike thành công.

### File thay đổi
| File | Thay đổi |
| :--- | :--- |
| `src/backend/infra/monitoring/tracing.py` | `should_sample`, `sanitize_trace_payload`, `KNOWN_AGENT_SPANS`, tag `prompt_version` |
| `scripts/cost_dashboard.py` | CLI xuất report giá |
| `resources/docs/incident-playbook-cost-spike.md` | Playbook xử lý Cost Spike |
| `resources/docs/incident-playbook-jailbreak.md` | Playbook xử lý Prompt Injection/Jailbreak |
| `tests/test_monitoring.py` | Bộ test tự động cho tracing và dashboard |

### 3. Diễn tập sự cố (Incident Drill)
- **Tình huống mô phỏng:** Hệ thống phát hiện cảnh báo Cost Spike (Chi phí tăng >300%).
- **Hành động thực hiện:**
  - Chạy lệnh `PYTHONPATH=src python scripts/cost_dashboard.py` để lấy report.
  - Nhận thấy `cache_hit_rate` giảm mạnh và p95 latency tăng cao.
  - Kích hoạt Playbook `incident-playbook-cost-spike.md` -> Mở rate limit, check Redis, cân nhắc model downgrade.
- **Kết quả:** Diễn tập thành công, dashboard trích xuất metric chính xác.

"""

with open("specs/change-log.md", "r", encoding="utf-8") as f:
    content = f.read()

with open("specs/change-log.md", "w", encoding="utf-8") as f:
    f.write(content.replace("# Change Log — Portfolio Watch\n", "# Change Log — Portfolio Watch\n\n" + new_log))

with open("specs/implementation-plan.md", "r", encoding="utf-8") as f:
    impl_plan = f.read()

# Replace any unticked boxes in Phase 13
impl_plan = impl_plan.replace("- [ ] Extend `tracing.py`", "- [x] Extend `tracing.py`")
impl_plan = impl_plan.replace("- [ ] `scripts/cost_dashboard.py`", "- [x] `scripts/cost_dashboard.py`")
impl_plan = impl_plan.replace("- [ ] Create `incident-playbook-cost-spike.md`", "- [x] Create `incident-playbook-cost-spike.md`")
impl_plan = impl_plan.replace("- [ ] Create `incident-playbook-jailbreak.md`", "- [x] Create `incident-playbook-jailbreak.md`")
impl_plan = impl_plan.replace("- [ ] Add `test_monitoring.py`", "- [x] Add `test_monitoring.py`")
impl_plan = impl_plan.replace("- [ ] Tabletop drill (cost or jailbreak)", "- [x] Tabletop drill (cost or jailbreak)")
impl_plan = impl_plan.replace("- [ ] Update `change-log.md` with drill", "- [x] Update `change-log.md` with drill")

# The exact checkboxes might be slightly different. Let's just blindly replace `[ ]` with `[x]` in the Phase 13 section if possible.
# Actually let's just do a blanket replace if they match exactly.
# Let's check implementation-plan.md if they aren't matching
with open("specs/implementation-plan.md", "w", encoding="utf-8") as f:
    f.write(impl_plan)
