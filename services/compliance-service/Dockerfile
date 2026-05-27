FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app/services/compliance-service:/app

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && pip install -r /app/requirements.txt

# libs/ provides libs.auth used to protect PUT /compliance/kill-switch.
COPY libs /app/libs
COPY services/compliance-service /app/services/compliance-service

RUN groupadd -r app && useradd -r -g app -u 10001 app && chown -R app:app /app
USER app

EXPOSE 8000

CMD ["uvicorn", "compliance_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
