# Parsing agy output

## JSON envelope (`--output-format json`)

Single line on stdout. Fields:

| Field | Use |
| --- | --- |
| `status` | `SUCCESS` or error terminal state |
| `response` | Free-text agent answer |
| `structured_output` | Parsed object when `--json-schema` was set |
| `conversation_id` | Resume with `--conversation` |
| `error` | Present on failure |
| `usage` | Token counts |
| `duration_seconds`, `num_turns` | Metrics |

### Extract with jq

```bash
jq -r '.response' .agy-runs/latest.json
jq '.structured_output' .agy-runs/latest.json
jq -r '.conversation_id' .agy-runs/latest.json
```

### Extract with Python

```python
import json
from pathlib import Path

data = json.loads(Path(".agy-runs/20260919-120000-explore.json").read_text())
if data.get("status") != "SUCCESS":
    raise RuntimeError(data.get("error") or data.get("status"))
text = data["response"]
verdict = data.get("structured_output")
```

## Stream JSON (`--output-format stream-json`)

NDJSON: one JSON object per line.

| `event` | Meaning |
| --- | --- |
| `init` | Session start (cwd, tools, permission_mode) |
| `step_update` | Progress; `text_delta` on agent_response |
| `result` | Final envelope (same shape as json mode) |

### Final result only

```bash
agy -p "..." --output-format stream-json | jq 'select(.event=="result") | .result'
```

### Concatenate streaming text

```bash
agy -p "..." --output-format stream-json \
  | jq -j 'select(.event=="step_update") | .step_update.text_delta // empty'
```

Wrapper with `--stream` saves the **full NDJSON** to the output file; parse the last `result` event for the answer.

## Wrapper output layout

```
.agy-runs/
  20260919-093012-explore.json    # raw agy stdout
  20260919-093012-explore.meta.json  # wrapper metadata (cmd, exit_code, parsed summary)
```

Read `.meta.json` for quick fields without re-parsing:

```json
{
  "task": "explore",
  "exit_code": 0,
  "status": "SUCCESS",
  "conversation_id": "...",
  "response_preview": "first 500 chars...",
  "output_file": ".agy-runs/20260919-093012-explore.json"
}
```

## Failure handling

| Condition | Action |
| --- | --- |
| `status != SUCCESS` | Surface `error` to user; do not treat as pass |
| Empty file / invalid JSON | Check agy version; read `cli.log` |
| exit_code != 0 | Read stderr from terminal + `error` field |
| Soft-denied tool in stderr | Adjust permissions or re-run with `--skip-permissions` |

## Resume conversation

```bash
python .cursor/skills/antigravity-cli/scripts/agy_run.py \
  --task ask \
  --prompt "Continue from where you left off" \
  --conversation "$(jq -r .conversation_id .agy-runs/last.meta.json)" \
  --cwd .
```
