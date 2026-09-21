---
name: antigravity-cli
description: >-
  Run Google Antigravity CLI (agy) headless for the right task type, capture
  machine-readable output, and parse results. Use when the user mentions agy,
  Antigravity CLI, antigravity, delegating work to agy, or orchestrating
  external agent tasks from Cursor with structured JSON output.
---

# Antigravity CLI (agy)

Orchestrate `agy` in headless mode (`-p`) from Cursor: pick flags by task type, run via the wrapper script, then read the saved JSON result.

## Prerequisites

1. **Install agy** (once): https://antigravity.google/docs/cli/install/
   - Windows binary: `%LOCALAPPDATA%\agy\bin\agy.exe`
2. **Authenticate** (once, interactive): run `agy` in a terminal and sign in.
   - CI/headless alternative: set `modelProvider: "gemini"` in `~/.gemini/antigravity-cli/settings.json` and export `GEMINI_API_KEY`.
3. **Verify**: `agy --version` and a smoke test:
   ```bash
   python .cursor/skills/antigravity-cli/scripts/agy_run.py --task ask --prompt "Reply with OK only"
   ```

## Quick start (always use the wrapper)

From the project root:

```bash
python .cursor/skills/antigravity-cli/scripts/agy_run.py \
  --task explore \
  --prompt "List the main API routes in backend/main.py" \
  --cwd .
```

The wrapper:
- Maps `--task` → **model + flags** (see [references/task-routing.md](references/task-routing.md))
- Auto-picks model per task (override with `--model`, env, or `--no-auto-model`)
- Forces `--output-format json` (or `stream-json` with `--stream`)
- Writes raw output to `.agy-runs/<timestamp>-<task>.json` (or `--output`)
- Prints a short summary (`status`, `response` preview, `conversation_id`)
- Exits non-zero if `status != SUCCESS` or stdout is empty

**After every run:** read the output file and use `response` / `structured_output` in your reply or next step.

## Workflow in Cursor

1. **Classify the user request** → pick a task type (table below).
2. **Draft a focused prompt** — include repo context, file paths, constraints, expected output format.
3. **Run** `agy_run.py` with `--cwd` set to the relevant repo.
4. **Parse result** — see [references/output-parsing.md](references/output-parsing.md).
5. **Continue or hand off** — use `conversation_id` with `--conversation` for follow-ups, or summarize for the user.

### Task type → when to use

| `--task` | Use when |
| --- | --- |
| `ask` | Pure Q&A, no file/shell tools needed |
| `explore` | Read-only codebase discovery |
| `review` | Code review, security/quality audit (read-heavy) |
| `implement` | Write/edit files, apply a spec or fix |
| `refactor` | Multi-file refactor with edits |
| `test` | Run tests/lint/build and report |
| `debug` | Investigate failures (logs, traces, repro) |
| `eval` | Structured verdict (pass/fail + fields) |

Full flag matrix: [references/task-routing.md](references/task-routing.md).

### Task → default model

| `--task` | Model | Lý do |
| --- | --- | --- |
| `ask` | `gemini-3.8-flash-medium` | Q&A nhanh |
| `explore` | `gemini-3.8-flash-medium` | Đọc codebase, tóm tắt |
| `review` | `claude-sonnet-4-6` | Audit sâu, thinking |
| `implement` | `gemini-3.1-pro-high` | Code chất lượng cao |
| `refactor` | `gemini-3.1-pro-high` | Multi-file refactor |
| `test` | `gemini-3.8-flash-medium` | Chạy test, báo cáo |
| `debug` | `claude-opus-4-6-thinking` | Suy luận sâu khi debug |
| `eval` | `gemini-3.1-pro-low` | Verdict có cấu trúc |

Override (ưu tiên cao → thấp): `--model` → `AGY_MODEL_<TASK>` → `AGY_MODEL` → `--no-auto-model` (để agy tự chọn).

```bash
# Ép model cho 1 lần chạy
python .cursor/skills/antigravity-cli/scripts/agy_run.py \
  --task implement --model claude-sonnet-4-6 --prompt "..." --cwd .

# Override mặc định implement cho cả project (bash)
export AGY_MODEL_IMPLEMENT=gemini-3.1-pro-high
```

## Prompt templates

### explore
```
You are exploring the repository at {cwd}.
Task: {goal}
Constraints: read-only; list files and quote paths; no edits.
Output: bullet summary + key file paths.
```

### implement
```
You are implementing in {cwd}.
Task: {goal}
Constraints: minimal diff; match existing style; run relevant tests if cheap.
Output: what changed, files touched, how to verify.
```

### review
```
Review the change or files: {paths}
Focus: correctness, edge cases, security.
Output: findings by severity (critical / suggestion / nit).
```

### eval
```
Golden case: {case_id}
Expected: {expected}
Run the eval command if needed, then judge pass/fail with reasons.
```

## Multi-turn

Save `conversation_id` from the JSON envelope, then:

```bash
python .cursor/skills/antigravity-cli/scripts/agy_run.py \
  --task ask \
  --prompt "Expand on the previous answer" \
  --conversation <conversation_id> \
  --cwd .
```

## Structured output (eval / machine checks)

```bash
python .cursor/skills/antigravity-cli/scripts/agy_run.py \
  --task eval \
  --prompt "Did the agent call PriceAgent? Reply JSON." \
  --schema '{"type":"object","properties":{"pass":{"type":"boolean"},"reason":{"type":"string"}},"required":["pass","reason"]}' \
  --cwd .
```

Read `structured_output` from the saved JSON file.

## Permissions

| Task | Default |
| --- | --- |
| `ask`, `explore`, `review` | No auto-approve (reads work in workspace) |
| `implement`, `refactor`, `test`, `debug` | `--dangerously-skip-permissions` via wrapper |

Override: pass `--no-skip-permissions` or `--skip-permissions` explicitly.

For production, prefer scoped rules in `~/.gemini/antigravity-cli/settings.json` under `permissions.allow` instead of blanket skip.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `agy: command not found` | Install CLI; on Windows ensure `%LOCALAPPDATA%\agy\bin` is on PATH |
| `x509: certificate signed by unknown authority` | Unset `SSL_CERT_FILE` (conda sets it) — wrapper does this; or `env -u SSL_CERT_FILE agy ...` |
| `authentication required` | Run interactive `agy` once, or configure Gemini API key path |
| Empty stdout, exit 0 | Upgrade agy; always use `--output-format json` (wrapper does this) |
| Tool soft-denied in stderr | Add `permissions.allow` rule or use `--skip-permissions` |
| Hangs in script | Set `--timeout`; for multi-turn use stream mode docs |

Logs: `~/.gemini/antigravity-cli/cli.log`

## Agent responsibilities

- **Do not** paste huge prompts inline in chat — put long context in a file and reference paths in the prompt.
- **Always** run the wrapper (not bare `agy`) so output is captured under `.agy-runs/`.
- **Always** read the output file after the command completes before claiming success.
- Prefer `json` for single-shot tasks; `--stream` only when the user wants live tool/progress visibility.

## References

- Task routing & flags: [references/task-routing.md](references/task-routing.md)
- JSON / stream-json parsing: [references/output-parsing.md](references/output-parsing.md)
- Official headless docs: https://antigravity.google/docs/cli/headless/
