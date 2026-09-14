FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

COPY src/chatbot/requirements.txt .
RUN pip install -r requirements.txt

COPY src/ src/

EXPOSE 8000
CMD ["uvicorn", "src.chatbot.main:app", "--host", "0.0.0.0", "--port", "8000"]
