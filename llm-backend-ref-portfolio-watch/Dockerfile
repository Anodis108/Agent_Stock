# Portfolio Watch — split demo image (AI / Backend / Frontend via compose command)
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
RUN pip install --no-cache-dir -U pip \
    && pip install --no-cache-dir -e .

# Prompt Registry; static UI at src/portfolio_watch/frontend (compose `frontend` service)
COPY prompts ./prompts

RUN mkdir -p /app/data

EXPOSE 8000 8001 5173

# Default = AI service; compose overrides command per service
CMD ["uvicorn", "src.portfolio_watch.ai_main:app", "--host", "0.0.0.0", "--port", "8001"]
