# Portfolio Watch — Backend Service Container (FastAPI + LangGraph Swarm)
# Build: docker build -f src/backend/Dockerfile -t portfolio-watch:backend .

# Stage 1: Builder
FROM python:3.12-slim AS builder

WORKDIR /build

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY wheels /wheels
COPY pyproject.toml README.md ./
RUN pip install --no-cache-dir -U pip setuptools wheel \
    && pip install --no-cache-dir /wheels/*.whl \
    && pip install --no-cache-dir .[dev]

# Stage 2: Final Runner
FROM python:3.12-slim AS runner

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends gosu \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH="/app/src:$PATH" \
    API_HOST=0.0.0.0 \
    API_PORT=8000 \
    SQLITE_PATH=/app/data/portfolio_watch.db \
    BACKEND_SQLITE_PATH=/app/data/backend_store.db

COPY --from=builder /opt/venv /opt/venv

COPY pyproject.toml README.md docker-compose.yml .env.example ./
COPY src ./src
COPY resources ./resources
COPY specs ./specs
COPY tests ./tests

# Link package in editable mode
RUN pip install --no-cache-dir --no-deps -e .

RUN mkdir -p /app/data /app/data/charts \
    && groupadd -r appuser --gid 10001 \
    && useradd -r -g appuser --uid 10001 --home-dir /app --shell /usr/sbin/nologin appuser \
    && chown -R appuser:appuser /app

COPY src/backend/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --retries=3 --start-period=10s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
