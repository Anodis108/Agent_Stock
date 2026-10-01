# GitHub Actions

Workflows live at the **monorepo root**: [`../../.github/workflows/`](../../.github/workflows/)

| File | Purpose |
| :--- | :--- |
| `ci.yml` | Prompt lint + pytest on PR/push |
| `eval-gate.yml` | Eval subset + gate + PR comment |
| `cd.yml` | Docker build + smoke test + LKG rollback |

Branch protection (GitHub → Settings → Branches → `main`):

- Require: `lint-and-test`, `eval-gate` (when triggered), `build-smoke-lkg`
- Repository secret: `OPENAI_API_KEYS` (eval gate only)
