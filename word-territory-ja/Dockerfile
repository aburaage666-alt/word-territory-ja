FROM python:3.11-slim

WORKDIR /app

COPY word-territory-ja/backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

COPY word-territory-ja/backend /app/backend
COPY word-territory-ja/frontend /app/frontend

ENV WT_LANG=ja
ENV PYTHONPATH=/app/backend

WORKDIR /app/backend

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
