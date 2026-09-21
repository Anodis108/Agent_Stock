# Task routing for agy

Map user intent → `agy_run.py --task` → agy CLI flags.

## Matrix

| Task | `--model` (auto) | `--output-format` | Skip permissions | `--effort` | Notes |
| --- | --- | --- | --- | --- | --- |
| `ask` | `gemini-3.8-flash-medium` | `json` | no | — | Single-turn Q&A |
| `explore` | `gemini-3.8-flash-medium` | `json` | no | `medium` | Read files, summarize |
| `review` | `claude-sonnet-4-6` | `json` | no | `high` | Read-only audit |
| `implement` | `gemini-3.1-pro-high` | `json` | **yes** | `medium` | Edits + optional test |
| `refactor` | `gemini-3.1-pro-high` | `json` | **yes** | `medium` | Multi-file changes |
| `test` | `gemini-3.8-flash-medium` | `json` | **yes** | `low` | Run test/lint commands |
| `debug` | `claude-opus-4-6-thinking` | `stream-json`* | **yes** | `high` | *Use `--stream` on wrapper |
| `eval` | `gemini-3.1-pro-low` | `json` | no† | `medium` | †Use `--schema` |

\* Default wrapper uses `json`; pass `--stream` for `debug` when tool steps matter.

## Decision tree

```
Need to write files or run shell?
  no  → ask | explore | review | eval (read-only)
  yes → implement | refactor | test | debug
Need structured pass/fail?
  yes → eval + --schema
Need live tool visibility?
  yes → debug + --stream
Multi-turn in one process?
  use agy stdin stream-json (advanced; see official docs)
```

## Model selection

Wrapper **tự gắn `--model`** theo bảng trên. List slugs: `env -u SSL_CERT_FILE agy models`

Override (ưu tiên cao → thấp):

1. `--model <slug>` — 1 lần chạy
2. `AGY_MODEL_IMPLEMENT=...` — theo task (uppercase task name)
3. `AGY_MODEL=...` — mọi task
4. `--no-auto-model` — không truyền `--model`, dùng default tài khoản agy

Ví dụ đổi model implement sang Claude:

```bash
export AGY_MODEL_IMPLEMENT=claude-sonnet-4-6
```

## Agent selection

List agents: `agy agents`

Use `--agent <name>` when the repo or user specifies a custom agent profile (e.g. security reviewer). Default: omit.

## Timeout

| Task | `--timeout` |
| --- | --- |
| `ask`, `explore` | `5m` (default) |
| `implement`, `refactor` | `15m` |
| `test`, `debug` | `20m` |

Override: `--timeout 10m` (wrapper accepts duration suffix `s`, `m`, `h`).

## Example commands

```bash
# Explore
python .cursor/skills/antigravity-cli/scripts/agy_run.py \
  --task explore \
  --prompt "Map the backend → AI HTTP flow" \
  --cwd .

# Implement
python .cursor/skills/antigravity-cli/scripts/agy_run.py \
  --task implement \
  --prompt "Add request_id to scan_symbol Langfuse metadata" \
  --cwd .

# Eval with schema
python .cursor/skills/antigravity-cli/scripts/agy_run.py \
  --task eval \
  --prompt "Run: python scripts/run_eval.py --case-id price_single. Check task_success." \
  --schema '{"type":"object","properties":{"pass":{"type":"boolean"},"case_id":{"type":"string"},"notes":{"type":"string"}},"required":["pass","case_id"]}' \
  --cwd .

# Debug with streaming
python .cursor/skills/antigravity-cli/scripts/agy_run.py \
  --task debug \
  --stream \
  --prompt "Why does case price_single fail? Read trajectory and fix root cause." \
  --cwd .
```

## Prompt hygiene

- Include **absolute or repo-relative paths** to files.
- State **done criteria** (tests pass, eval case id, files changed).
- For implement/refactor: mention **style rules** (minimal diff, no new deps).
- For eval: give exact **command** and **expected fields** from golden YAML.
