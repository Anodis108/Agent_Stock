FROM python:3.11-slim-bullseye

RUN apt-get update \
    && apt-get install libmagic1 swig wget -y \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install ffmpeg libsm6 libxext6  -y

WORKDIR /app

COPY logic_app/requirements.txt .

# Upgrade pip
RUN pip install --upgrade pip

# Increase timeout to wait for the new installation
RUN pip install --no-cache-dir -r requirements.txt --timeout 200
