# Portfolio Watch — demo image (API + static web/)
# Build: docker build -t portfolio-watch .
# Run:   docker run --rm -p 8000:8000 --env-file .env portfolio-watch

FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    API_HOST=0.0.0.0 \
    API_PORT=8000 \
    SQLITE_PATH=/app/data/portfolio_watch.db

# Dependencies first (layer cache)
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir -U pip \
    && pip install --no-cache-dir -e .
# Editable: __file__ vẫn dưới /app/src → WEB_DIR=/app/web (StaticFiles)

# Static UI (served by FastAPI at /)
COPY web ./web

RUN mkdir -p /app/data

EXPOSE 8000

# Production-like demo: no --reload
CMD ["uvicorn", "src.portfolio_watch.main:app", "--host", "0.0.0.0", "--port", "8000"]
