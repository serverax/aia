FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

WORKDIR /app

# rag_system is self-contained (qdrant-client, sentence-transformers, anthropic)
# and does not import libs/, so only its own requirements are installed.
# NOTE: per the Milvus decision, the canonical analyst RAG path will move to
# Milvus; this image packages the current Qdrant-backed service as-is.
COPY services/rag_system/requirements.txt /app/services/rag_system/requirements.txt
RUN pip install --upgrade pip && pip install -r /app/services/rag_system/requirements.txt

COPY services/rag_system /app/services/rag_system

RUN groupadd -r app && useradd -r -g app -u 10001 app && chown -R app:app /app
USER app

EXPOSE 8000

CMD ["uvicorn", "services.rag_system.rag_service:app", "--host", "0.0.0.0", "--port", "8000"]
