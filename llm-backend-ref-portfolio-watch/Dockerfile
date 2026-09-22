# Portfolio Watch V3 — single product container (UI + API + LangGraph in-process)
# Build: docker build -t portfolio-watch:split .
# Compose: docker compose up --build

FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    API_HOST=0.0.0.0 \
    API_PORT=8000 \
    AI_API_HOST=0.0.0.0 \
    AI_API_PORT=8001 \
    SQLITE_PATH=/app/data/portfolio_watch.db \
    BACKEND_SQLITE_PATH=/app/data/backend_store.db

# Dependencies first (layer cache)
COPY pyproject.toml README.md ./
COPY src ./src
# setuptools/wheel trước: build isolation đôi khi không fetch được từ PyPI
RUN pip install --no-cache-dir -U pip setuptools wheel \
    && pip install --no-cache-dir --no-build-isolation -e .

# Prompt Registry; static UI at src/portfolio_watch/frontend
COPY prompts ./prompts

RUN mkdir -p /app/data

EXPOSE 8000

# Default = product service (FastAPI backend + static UI + in-process LangGraph)
CMD ["uvicorn", "src.portfolio_watch.backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
