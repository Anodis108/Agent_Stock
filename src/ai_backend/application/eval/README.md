# application/eval

Golden eval **use cases & CLI**: `runner`, `run`, `regression`, `run_detailed`, `run_excel_export`.

Scorers, dataset, gate policy, cache, history: **`ai_backend.infra.eval`**.

```bash
python -m ai_backend.application.eval.run
python -m ai_backend.application.eval.gate --run specs/eval/pr_report.json
```

Gate CLI re-exports `check_gates` from infra; CI may keep `from ai_backend.application.eval.gate import check_gates`.
