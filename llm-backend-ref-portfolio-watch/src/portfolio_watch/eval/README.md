# eval/

Golden dataset runner + full regression gate.

```bash
python -m src.portfolio_watch.eval.run --self-check
python -m src.portfolio_watch.eval.regression
```

Docker: `docker compose run --rm ai python -m src.portfolio_watch.eval.run --run --case-id lookup_01`
