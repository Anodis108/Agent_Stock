You are implementing Phase 13 in the repository at cwd.

## Goal (specs/implementation-plan.md Phase 13 — M3-B7 Observability + Playbook)

### 1. Extend `src/backend/infra/monitoring/tracing.py`
Add:
- `should_sample(*, is_error: bool = False, is_guardrail: bool = False, latency_s: float | None = None, slow_threshold_s: float = 5.0, normal_rate: float = 0.05) -> bool`
  - Return True always for error, guardrail block, or slow requests (latency >= threshold)
  - Return True ~5% for normal requests (use deterministic hash of optional seed or random)
- `redact_pii(text: str) -> str` — mask phone numbers and emails before trace export
- `sanitize_trace_payload(data: Any) -> Any` — recursively redact strings in dict/list for trace input/output
- Integrate `should_sample()` into `trace_request()` — skip creating Langfuse trace when sample=False (no-op yield)
- Integrate `sanitize_trace_payload()` on input/output passed to spans
- Add `KNOWN_AGENT_SPANS` constant listing: guardrail, rewrite, supervisor, price, news, chart, composer (and aliases used in graph/chat.py)
- Tag LLM generations with `prompt_version` in metadata when available from cost context

Read existing graph/chat.py agent_span names: pre_rewrite_guardrail, guardrail_refusal, rewrite_question, supervisor, price_agent, news_agent, chart_agent, answer_composer.

### 2. `scripts/cost_dashboard.py`
CLI script reporting >= 3 metrics from cost tracker / eval history:
- Total cost (USD/VND)
- p95 latency (from eval history JSON files in specs/eval/history/ if available, else from tracker summary)
- Cache hit rate
Output markdown to specs/eval/cost_dashboard.md and JSON summary.
Support: `PYTHONPATH=src python scripts/cost_dashboard.py`

Use existing `backend.infra.cost.tracker.get_cost_tracker()` and read latest files in `specs/eval/history/` for latency if present.

### 3. Playbooks
Create:
- `resources/docs/incident-playbook-cost-spike.md` — detection, triage, actions (cache, rate limit, model downgrade), escalation
- `resources/docs/incident-playbook-jailbreak.md` — detection via guardrail/eval, rollback prompt, HITL review

Vietnamese or bilingual OK, match project doc style.

### 4. Tests — `tests/test_monitoring.py`
- test_should_sample_always_on_guardrail_and_error
- test_should_sample_normal_rate_approx_5_percent (statistical or seeded)
- test_redact_pii_phone_and_email
- test_sanitize_trace_payload_nested
- test_trace_request_skips_when_not_sampled (mock)
- test_cost_dashboard_script_runs (subprocess or import main)

### 5. Incident drill
Run a tabletop drill for ONE playbook (cost-spike OR jailbreak). Append drill log entry to specs/change-log.md with timestamp + actions taken (simulated OK).

### 6. Mark complete
Update specs/implementation-plan.md Phase 13 all items [x].

## Existing patterns
- tracing.py already has trace_request, agent_span, trace_step, record_step_usage
- cost tracker: src/backend/infra/cost/tracker.py
- cost_baseline.py in scripts/ for reference
- tests/test_agents.py has mock Langfuse tracing tests

## Constraints
- Minimal diff; no unrelated changes
- Monitoring stays no-op when MONITORING_ENABLED=false
- Run: PYTHONPATH=src pytest tests/test_monitoring.py -v
- Run: PYTHONPATH=src python scripts/cost_dashboard.py

## Output
List files changed and test results.
