# Backend runtime image — Python venv + gosu only. NO application code.
# Code, entrypoint, command, healthcheck → docker-compose.yml
# Rebuild when pyproject.toml dependencies change:
#   docker compose build backend

FROM python:3.12-slim AS builder

WORKDIR /build

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY pyproject.toml README.md ./

ARG PIP_EXTRA_INDEX_URL=https://vnstocks.com/api/simple
ENV PIP_EXTRA_INDEX_URL=${PIP_EXTRA_INDEX_URL}

RUN pip install --no-cache-dir -U pip setuptools wheel \
    && python - <<'PY'
import os
import subprocess
import tomllib
from pathlib import Path

data = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
deps = list(data["project"]["dependencies"])
deps.extend(data["project"].get("optional-dependencies", {}).get("dev", []))
extra = os.environ.get("PIP_EXTRA_INDEX_URL")
cmd = ["pip", "install", "--no-cache-dir"]
if extra:
    cmd.extend(["--extra-index-url", extra])
cmd.extend(deps)
subprocess.check_call(cmd)
PY

FROM python:3.12-slim AS runner

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends gosu \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

COPY --from=builder /opt/venv /opt/venv

RUN mkdir -p /app/data /app/data/charts \
    && groupadd -r appuser --gid 10001 \
    && useradd -r -g appuser --uid 10001 --home-dir /app/data --shell /usr/sbin/nologin appuser
