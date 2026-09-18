# Phase 5 Regression Report — Full golden sau FE/BE

**Ngày:** 2026-09-18
**Baseline:** `specs/eval/baseline_debug.json` (rate=100%)
**Scorer:** rule-based (`--skip-judge --skip-agent-eval`)
**Runner:** `python scripts/phase5_regression.py`

## Kết quả

| Slice | Passed | Total | Rate |
|---|---:|---:|---:|
| lookup | 18 | 18 | 100% |
| comparison | 6 | 6 | 100% |
| out_of_scope | 3 | 3 | 100% |
| injection | 3 | 3 | 100% |
| **Tổng** | **30** | **30** | **100%** |

- **Regression vs baseline_debug:** OK (drop=0.0000, tolerance=0.05)
- **Injection gate:** OK (cần 100%)
- **Failures:** (none)

## Tái hiện

```bash
unset SSL_CERT_FILE
python scripts/phase5_regression.py --case-delay 20
```

