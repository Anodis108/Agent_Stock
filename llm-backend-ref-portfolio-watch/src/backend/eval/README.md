# eval/

Golden dataset runner + full regression gate.

```bash
python -m backend.eval.run --self-check
python -m backend.eval.regression
```

Docker: `docker compose run --rm app python -m backend.eval.run --run --case-id lookup_01`
