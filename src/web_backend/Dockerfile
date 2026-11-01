# Multi-stage Dockerfile cho Web Backend Microservice (Cổng 8000)

# Stage 1: Build virtual environment và dependencies
FROM python:3.12-slim AS builder

WORKDIR /build

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt ./

ARG PIP_EXTRA_INDEX_URL=https://vnstocks.com/api/simple
ENV PIP_EXTRA_INDEX_URL=${PIP_EXTRA_INDEX_URL}

# Chỉ runtime deps (requirements.txt) — pytest/ruff ở requirements-dev.txt, không vào image.
RUN pip install --no-cache-dir -U pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime image tối ưu và bảo mật
FROM python:3.12-slim AS runner

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gosu \
    curl \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH="/app/src" \
    PORT=8000 \
    HOST=0.0.0.0

COPY --from=builder /opt/venv /opt/venv

# Tạo người dùng không đặc quyền (non-root)
RUN mkdir -p /app/resources/data /app/resources/data/charts \
    && groupadd -r appuser --gid 10001 \
    && useradd -r -g appuser --uid 10001 --home-dir /app/resources/data --shell /usr/sbin/nologin appuser \
    && chown -R appuser:appuser /app/resources/data

COPY src/ /app/src/
COPY resources/ /app/resources/

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "web_backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
