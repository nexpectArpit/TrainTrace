FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    TRAINTRACE_STORAGE_DIR=/data/storage \
    TRAINTRACE_LIGHTWEIGHT_INFO=1

WORKDIR /app

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --upgrade pip && pip install -r /app/backend/requirements.txt

COPY backend /app/backend
RUN mkdir -p /data/storage

EXPOSE 8000

CMD ["sh", "-c", "uvicorn api.main:app --app-dir /app/backend --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]

