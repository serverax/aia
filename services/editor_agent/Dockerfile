FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

WORKDIR /app

# Editor uses libs.communication (Redis streams + Postgres audit + OTel), all
# of which live in the root requirements. The default Markdown renderer needs
# no extra system packages; wiring the real DOCX/PDF generator later will add
# its own deps (e.g. pandoc) here.
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && pip install -r /app/requirements.txt

COPY libs /app/libs
COPY services/editor_agent /app/services/editor_agent

RUN groupadd -r app && useradd -r -g app -u 10001 app && chown -R app:app /app
USER app

EXPOSE 8000

CMD ["uvicorn", "services.editor_agent.main:app", "--host", "0.0.0.0", "--port", "8000"]
