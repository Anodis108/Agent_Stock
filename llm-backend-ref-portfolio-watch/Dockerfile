# Portfolio Watch — Backend Service Container (FastAPI + LangGraph Swarm)
# Build: docker build -t portfolio-watch:backend .

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

RUN mkdir -p /app/data /app/data/charts

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
