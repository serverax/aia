FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

WORKDIR /app

COPY requirements.txt /app/requirements.txt
COPY services/analyst_agent/requirements.txt /app/services/analyst_agent/requirements.txt
RUN pip install --upgrade pip && pip install -r /app/services/analyst_agent/requirements.txt

COPY libs /app/libs
COPY services/analyst_agent /app/services/analyst_agent
COPY services/tool_sandbox /app/services/tool_sandbox

RUN groupadd -r app && useradd -r -g app -u 10001 app && chown -R app:app /app
USER app

EXPOSE 8000

CMD ["uvicorn", "services.analyst_agent.main:app", "--host", "0.0.0.0", "--port", "8000"]
