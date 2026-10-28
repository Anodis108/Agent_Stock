# observability

| Demo (Module III Bài 7) | vn-stock hiện tại |
|-------------------------|-------------------|
| `observability/metrics.py` — trace tags | Chưa tách file; metadata trong `infra/monitoring/tracing.py` |
| `observability/sampling.py` — tail sampling | Không dùng |
| `observability/redaction.py` — PII trước export | `infra/observability/redaction.py` (+ `domain/guardrails/pii.py`), gắn qua `mask=` của Langfuse client |
| `observability/feedback.py` | `web_backend` HITL + `hitl_repo` |

Phase sau: tách tag keys + redaction helper ra module riêng nếu cần parity demo.
