# SSE / LLM Concurrency Benchmark — Portfolio Watch (Phase 10)

- **Generated:** 2026-09-28T15:06:25Z
- **Git SHA:** `792fa34`
- **Method:** Simulated LLM job (200ms) × 50 concurrent requests

## p50 / p95 theo LLM_SEMAPHORE

| LLM_SEMAPHORE | Requests | Peak concurrent | Wall (s) | p50 (s) | p95 (s) | max (s) |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 5 | 50 | 5 | 2.223 | 1.053 | 2.1342 | 2.2048 |
| 20 | 50 | 20 | 1.189 | 0.2312 | 0.4663 | 0.6146 |

## Ghi chú

- Semaphore 5 giới hạn peak concurrent ≤ 5; semaphore 20 cho phép cao hơn → p95 thấp hơn.
- Benchmark này mô phỏng slot LLM; live SSE cần `docker compose up` + API key.
- Chạy: `PYTHONPATH=src python scripts/benchmark_sse.py`
