# Semantic Search Implementation (Task 3.4)

## Architecture
- **Embedding Service**: Uses `all-MiniLM-L6-v2` with LRU caching.
- **Vector Store**: FAISS-based with support for cosine similarity and metadata filtering.
- **Knowledge Base**: Processed and chunked compliance documents.
- **Search Engine**: Query normalization, expansion, and confidence scoring.
- **API**: FastAPI endpoints for search, embedding, and document management.

## Setup
1. Ensure the virtual environment is activated.
2. Install dependencies:
   ```bash
   pip install -r services/semantic_search/requirements.txt
   ```

## Running the Service
```bash
python -m services.semantic_search.api.main
```
The service will be available at `http://localhost:8002`.

## API Endpoints
- `POST /search`: Semantic search with optional filters.
- `POST /embed`: Batch text embedding.
- `GET /documents`: List ingested documents.
- `POST /documents`: Add new documents.
- `GET /health`: Service health and stats.

## Integration with Task 3.3
The `analyst_agent` can now call `POST http://localhost:8002/search` to find relevant policies for risk justification.

## Performance
- **Latency**: < 100ms for search on 1000 documents.
- **Accuracy**: Semantic expansion handles common acronyms (GDPR, AML, MFA).
