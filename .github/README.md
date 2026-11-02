# GitHub Actions

Workflows live at the **monorepo root**: [`../../.github/workflows/`](../../.github/workflows/)

| File | Purpose |
| :--- | :--- |
| `ci.yml` | Job `checks` (prompt lint + ruff) rồi `tests` (pytest); eval tách `eval-gate.yml` |
| `eval-gate.yml` | PR subset + gate; nightly full; cache `.eval_cache` |
| `deploy.yml` | **Demo / mặc định:** compose trên runner → smoke → LKG cache rollback |
| `cd.yml` | **Production (tắt mặc định):** SSH host + `release.sh`; bật `ENABLE_SSH_DEPLOY=true` |

Branch protection (GitHub → Settings → Branches → `main`):

- Require: `checks`, `tests`, `eval-gate` (when triggered), `build-smoke-lkg`
- Repository secret: `OPENAI_API_KEYS` (eval gate); `VM_SSH_KEY` (chỉ khi bật `cd.yml`)
- Variables (cd.yml): `ENABLE_SSH_DEPLOY`, `VM_HOST`, `VM_USER`, optional `APP_DIR`, `APP_URL`

Không bật `deploy.yml` drill và `cd.yml` SSH vào **cùng một** máy production cùng lúc.
