#!/usr/bin/env python3
"""Run Antigravity CLI (agy) headless with task-aware defaults and captured output."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# Default model per task (slugs from `agy models`). Override: --model, AGY_MODEL, AGY_MODEL_<TASK>.
TASKS = {
    "ask": {
        "skip_permissions": False,
        "effort": None,
        "timeout": "5m",
        "stream": False,
        "model": "gemini-3.8-flash-medium",
    },
    "explore": {
        "skip_permissions": False,
        "effort": "medium",
        "timeout": "5m",
        "stream": False,
        "model": "gemini-3.8-flash-medium",
    },
    "review": {
        "skip_permissions": False,
        "effort": "high",
        "timeout": "10m",
        "stream": False,
        "model": "claude-sonnet-4-6",
    },
    "implement": {
        "skip_permissions": True,
        "effort": None,
        "timeout": "15m",
        "stream": False,
        "model": "gemini-3.1-pro-high",
    },
    "refactor": {
        "skip_permissions": True,
        "effort": None,
        "timeout": "15m",
        "stream": False,
        "model": "gemini-3.1-pro-high",
    },
    "test": {
        "skip_permissions": True,
        "effort": "low",
        "timeout": "20m",
        "stream": False,
        "model": "gemini-3.8-flash-medium",
    },
    "debug": {
        "skip_permissions": True,
        "effort": "high",
        "timeout": "20m",
        "stream": True,
        "model": "claude-opus-4-6-thinking",
    },
    "eval": {
        "skip_permissions": False,
        "effort": None,
        "timeout": "15m",
        "stream": False,
        "model": "gemini-3.1-pro-low",
    },
}


def resolve_effort(model: str | None, effort: str | None) -> str | None:
    """Model slug -high/-low/-medium already sets tier; agy rejects duplicate --effort."""
    if not effort or not model:
        return effort
    if re.search(r"-(?:high|low|medium)$", model):
        return None
    return effort


def resolve_model(task: str, cfg: dict, explicit: str | None, no_auto: bool) -> str | None:
    if explicit:
        return explicit
    if no_auto:
        return None
    env_task = os.environ.get(f"AGY_MODEL_{task.upper()}")
    if env_task:
        return env_task
    env_default = os.environ.get("AGY_MODEL")
    if env_default:
        return env_default
    return cfg.get("model")


def find_agy() -> str:
    found = shutil.which("agy")
    if found:
        return found
    if sys.platform == "win32":
        local = os.environ.get("LOCALAPPDATA", "")
        if local:
            candidate = Path(local) / "agy" / "bin" / "agy.exe"
            if candidate.is_file():
                return str(candidate)
    raise FileNotFoundError(
        "agy not found. Install from https://antigravity.google/docs/cli/install/"
    )


def slug(text: str, max_len: int = 40) -> str:
    s = re.sub(r"[^a-zA-Z0-9_-]+", "-", text.strip().lower()).strip("-")
    return (s[:max_len] or "run")


def parse_json_stdout(raw: str) -> dict | None:
    raw = raw.strip()
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    for line in reversed(raw.splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and "event" in obj and obj.get("event") == "result":
            return obj.get("result")
        if isinstance(obj, dict) and "status" in obj:
            return obj
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Run agy headless with task-aware defaults")
    parser.add_argument("--task", choices=sorted(TASKS), required=True)
    parser.add_argument("--prompt", "-p", required=True)
    parser.add_argument("--cwd", default=os.getcwd())
    parser.add_argument("--output", "-o", help="Output file path (default: .agy-runs/<timestamp>-<task>.json)")
    parser.add_argument("--model", help="Model slug (agy models); overrides task default")
    parser.add_argument(
        "--no-auto-model",
        action="store_true",
        help="Do not pass --model; use agy account default",
    )
    parser.add_argument("--agent", help="Agent name (agy agents)")
    parser.add_argument("--schema", help="JSON schema string or path for structured output")
    parser.add_argument("--conversation", help="Resume conversation by ID")
    parser.add_argument("--stream", action="store_true", help="Use stream-json output")
    parser.add_argument("--skip-permissions", action="store_true")
    parser.add_argument("--no-skip-permissions", action="store_true")
    parser.add_argument("--timeout", help="Override print timeout e.g. 10m")
    parser.add_argument("--effort", choices=["low", "medium", "high"])
    args = parser.parse_args()

    cfg = TASKS[args.task]
    agy = find_agy()
    use_stream = args.stream or cfg["stream"]
    output_format = "stream-json" if use_stream else "json"

    skip = cfg["skip_permissions"]
    if args.skip_permissions:
        skip = True
    if args.no_skip_permissions:
        skip = False

    cmd: list[str] = [
        agy,
        "-p",
        args.prompt,
        "--output-format",
        output_format,
        "--print-timeout",
        args.timeout or cfg["timeout"],
    ]
    model = resolve_model(args.task, cfg, args.model, args.no_auto_model)
    effort = resolve_effort(model, args.effort or cfg["effort"])
    if effort:
        cmd.extend(["--effort", effort])
    if model:
        cmd.extend(["--model", model])
    if args.agent:
        cmd.extend(["--agent", args.agent])
    if args.conversation:
        cmd.extend(["--conversation", args.conversation])
    if args.schema:
        schema = args.schema
        if Path(schema).is_file():
            schema = Path(schema).read_text(encoding="utf-8")
        cmd.extend(["--json-schema", schema])
    if skip:
        cmd.append("--dangerously-skip-permissions")

    cwd = Path(args.cwd).resolve()
    if not cwd.is_dir():
        print(f"error: --cwd not a directory: {cwd}", file=sys.stderr)
        return 1

    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    out_dir = cwd / ".agy-runs"
    out_dir.mkdir(exist_ok=True)
    out_file = Path(args.output) if args.output else out_dir / f"{ts}-{args.task}.json"
    meta_file = out_file.with_suffix(".meta.json")

    print(f"running: {' '.join(cmd[:6])} ...", file=sys.stderr)
    print(f"task: {args.task}, model: {model or '(agy default)'}", file=sys.stderr)
    print(f"cwd: {cwd}", file=sys.stderr)
    print(f"output: {out_file}", file=sys.stderr)

    # Conda sets SSL_CERT_FILE → Go (agy) skips Windows cert store → TLS fail.
    env = os.environ.copy()
    env.pop("SSL_CERT_FILE", None)
    env.pop("SSL_CERT_DIR", None)

    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    stdout = proc.stdout or ""
    stderr = proc.stderr or ""
    out_file.write_text(stdout, encoding="utf-8")

    parsed = parse_json_stdout(stdout)
    status = parsed.get("status") if parsed else None
    response = (parsed.get("response") or "") if parsed else ""
    conversation_id = parsed.get("conversation_id") if parsed else None
    error = parsed.get("error") if parsed else None
    structured = parsed.get("structured_output") if parsed else None

    meta = {
        "task": args.task,
        "model": model,
        "cmd": cmd,
        "cwd": str(cwd),
        "exit_code": proc.returncode,
        "status": status,
        "error": error,
        "conversation_id": conversation_id,
        "response_preview": response[:500],
        "structured_output": structured,
        "output_file": str(out_file),
        "stderr_tail": stderr[-2000:] if stderr else "",
    }
    meta_file.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

    if stderr:
        print(stderr, file=sys.stderr)

    if not stdout.strip():
        print("error: agy produced empty stdout (upgrade agy; use --output-format json)", file=sys.stderr)
        return proc.returncode or 1

    if parsed is None:
        print("warning: could not parse JSON from stdout; see output file", file=sys.stderr)
        return proc.returncode or 1

    print(json.dumps({"status": status, "conversation_id": conversation_id, "output_file": str(out_file)}, indent=2))
    if structured is not None:
        print("structured_output:", json.dumps(structured, indent=2, ensure_ascii=False))
    elif response:
        preview = response[:800] + ("..." if len(response) > 800 else "")
        print("response:", preview)

    if proc.returncode != 0:
        return proc.returncode
    if status and status != "SUCCESS":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
