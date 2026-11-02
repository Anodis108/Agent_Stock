---
name: antigravity-cli
description: >-
  MUST delegate coding to agy via agy_run.py (never Cursor Write/StrReplace for
  app code when this skill applies). ALWAYS orchestrate with Superpowers
  (using-superpowers first each turn) and vn-stock-swarm SDD (specs/, AGENTS.md).
  Use when the user mentions agy, Antigravity, antigravity-cli, or delegates
  implement/refactor/debug/test to Antigravity.
---

# Antigravity CLI (agy) — Superpowers + SDD + agy

When **this skill applies**, Cursor is the **orchestrator** (Superpowers + SDD); **agy** performs file edits and test runs.

## Mandatory Superpowers (every time this skill is invoked)

1. Read and follow the Superpowers plugin skill **`using-superpowers`** before responding or running agy. Announce: `Using [skill] to …`.
2. **Route before agy:**
   | Situation | Superpowers skill first |
   | --- | --- |
   | New feature / behavior change | `brainstorming` — user approves design; update `specs/` if needed |
   | Bug | `systematic-debugging` |
   | Code change | `test-driven-development` when adding/changing behavior |
   | Claiming done | `verification-before-completion` — run verify commands, cite output |
3. **Project rule:** `.cursor/rules/antigravity-superpowers.mdc` (same requirements).

## Mandatory SDD (vn-stock-swarm)

- Read `AGENTS.md` and relevant files under `specs/` before the first agy call for a task.
- Implement **one** unchecked `[ ]` in `specs/implementation-plan.md` per cycle unless the user scopes otherwise.
- After successful agy run: tick checklist, update `specs/change-log.md`, report tests per `AGENTS.md` §5.
- Do not add libraries outside `pyproject.toml` or break Golden v6 offline tests.

## Hard rule (non-negotiable) — coding via agy only

1. **Do NOT** write, edit, or refactor application code with Cursor `Write`, `StrReplace`, or `EditNotebook` for the coding goal.
2. **MUST** run agy through the wrapper:
   ```bash
   python .cursor/skills/antigravity-cli/scripts/agy_run.py \
     --task implement \
     --prompt "…" \
     --cwd "d:/Hoc_Tap/YOURClass/Project/vn-stock-swarm"
   ```
   Use absolute `--cwd` to this repo (or `.` from repo root).
3. **Allowed in Cursor:** read-only discovery (`Read`, `Grep`, `Glob`), draft agy prompts, run wrapper, read `.agy-runs/*.json`, summarize, `--conversation` follow-ups.
4. If agy is missing or auth fails: **stop** and tell the user how to install/sign in. Do **not** fall back to Cursor coding unless the user says **“bỏ Antigravity, bạn code giúp”**.

Orchestrate `agy` in headless mode (`-p`): pick flags by task type, run via the wrapper script, then read the saved JSON result.

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

### Model fallback (tự động)

Wrapper **ưu tiên model phù hợp task**, nếu lỗi eligibility / 503 / 429 / model không nhận → thử `model_fallbacks` trong `agy_run.py` (ghi `AGY_MODEL_FALLBACK` trên stderr + `.meta.json`).

| Task | Model chính | Fallback |
| --- | --- | --- |
| `implement` / `refactor` | `gemini-3.1-pro-high` | pro-low → flash-medium → flash-high |
| `review` | `claude-sonnet-4-6` | pro-high → pro-low → flash |
| `debug` | `claude-opus-4-6-thinking` | sonnet → pro-high → flash |
| `eval` | `gemini-3.1-pro-low` | flash-medium → flash-high |

Tắt fallback: `--no-model-fallback`. Ép 1 model cố định: `--model <slug>` (không fallback).

```bash
# Ép model cho 1 lần chạy (không fallback)
python .cursor/skills/antigravity-cli/scripts/agy_run.py \
  --task implement --model claude-sonnet-4-6 --no-model-fallback --prompt "..." --cwd .

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
You are implementing in {cwd} (vn-stock-swarm SDD).
Task: {goal} — checklist item: {implementation-plan ref}
Spec context: read specs/product-spec.md, specs/test-plan.md as needed.
Constraints: minimal diff; match existing style; one plan checkbox; no new deps;
offline tests (Golden v6 must stay green); follow AGENTS.md architecture boundaries.
TDD: write/adjust failing tests first when behavior changes, then make them pass.
Output: files touched, pytest commands run + results, how to verify manually.
After edits: user/orchestrator will tick implementation-plan and update specs/change-log.md.
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
| `503` / Eligibility / quota trên Pro | Wrapper tự fallback Flash (xem stderr `AGY_MODEL_FALLBACK`) |
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
