# Hiring API image. Build from the repo root so the shared `libs/` and the
# root requirements.txt are in the build context:
#
#   docker build -f apps/api/Dockerfile -t aia-hiring-api:0.1.0 .
#
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

WORKDIR /app

COPY requirements.txt /app/requirements.txt
COPY apps/api/requirements.txt /app/apps/api/requirements.txt
RUN pip install --upgrade pip && pip install -r /app/apps/api/requirements.txt

COPY libs /app/libs
COPY apps /app/apps

RUN groupadd -r app && useradd -r -g app -u 10001 app && chown -R app:app /app
USER app

EXPOSE 8080

# Honour $PORT if the platform injects one; default 8080.
CMD ["sh", "-c", "uvicorn apps.api.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
