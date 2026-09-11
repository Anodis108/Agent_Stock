FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
# Package Python của Playwright được cài (import trễ bởi render_fetcher.py)
# nhưng browser binary thì KHÔNG — image này dùng cho scout/document/api/
# stealth/query-api, không cái nào gọi tới Playwright cả. Xem Dockerfile.render
# cho image thật sự chạy RenderAgent.
RUN pip install -r requirements.txt

COPY src/ src/

RUN useradd --create-home --uid 1000 crawler && \
    mkdir -p /data && chown -R crawler:crawler /app /data
USER crawler

ENTRYPOINT ["python", "-m", "main"]
