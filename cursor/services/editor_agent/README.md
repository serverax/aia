# Editor Agent Service

FastAPI service for Sprint 5 document finalization.

## Endpoints

- `GET /api/v1/health`
- `GET /api/v1/templates`
- `POST /api/v1/templates/{template_id}/render`
- `POST /api/v1/generate/docx`
- `POST /api/v1/generate/pdf`
- `GET /api/v1/documents/{doc_id}/download`

## Run

```bash
pip install -r requirements.txt
uvicorn api.main:app --reload --port 8010
```

