FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

WORKDIR /app

# WebSocket support comes from uvicorn[standard] in the root requirements.
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && pip install -r /app/requirements.txt

COPY libs /app/libs
COPY services/realtime_collab /app/services/realtime_collab

RUN groupadd -r app && useradd -r -g app -u 10001 app && chown -R app:app /app
USER app

EXPOSE 8000

CMD ["uvicorn", "services.realtime_collab.main:app", "--host", "0.0.0.0", "--port", "8000"]
