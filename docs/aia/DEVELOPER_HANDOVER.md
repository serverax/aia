# Developer Handover - AIA Hiring Webapp

## Environment

DEV base domain:

`dev.ordinoxai.com`

Main namespace:

`aia-dev`

Internal LLM endpoint:

`http://aia-ollama-dev-cpu.aia-dev.svc.cluster.local:11434`

Internal object storage endpoint:

`http://minio-dev.aia-dev-storage.svc.cluster.local:9000`

## Database Schemas

Use these schemas in DEV:

- `orchestrator_dev`
- `rag_dev`
- `semantic_dev`

## Orchestrator Service

Use:

- `orchestrator_dev.jobs`
- `orchestrator_dev.job_status`
- `orchestrator_dev.agent_config`
- `orchestrator_dev.agent_status`

Expected workflow:

1. API creates job in `orchestrator_dev.jobs`
2. Worker locks job
3. Worker updates `job_status`
4. Worker calls RAG/search/LLM
5. Worker stores final result in job status metadata or application tables

## RAG Service

Use:

- `rag_dev.documents`
- `rag_dev.embeddings`
- `rag_dev.queries`
- `rag_dev.results`

Expected workflow:

1. Upload CV/job document to storage
2. Extract text
3. Chunk content
4. Store chunks in `rag_dev.documents`
5. Generate embeddings
6. Store vectors in `rag_dev.embeddings`
7. Query and store retrieval audit in `rag_dev.queries` and `rag_dev.results`

## Semantic Search Service

Use:

- `semantic_dev.indexes`
- `semantic_dev.documents`
- `semantic_dev.embeddings`

Initial indexes:

- `candidate-cv-dev-index`
- `job-description-dev-index`
- `interview-qa-dev-index`

## Required Application Services

The developer should create or connect:

| Service | Expected path |
|---|---|
| Web frontend | `apps/web` |
| API backend | `apps/api` |
| Orchestrator worker | `services/orchestrator` |
| RAG worker | `services/rag` |
| Search worker | `services/search` |

Each deployable service should include a Dockerfile.

The GitHub build pipeline detects:

- `apps/web/Dockerfile`
- `apps/api/Dockerfile`
- `services/orchestrator/Dockerfile`
- `services/rag/Dockerfile`
- `services/search/Dockerfile`

## Required API Endpoints

Minimum API endpoints:

| Endpoint | Purpose |
|---|---|
| `GET /health` | Basic process health |
| `GET /ready` | DB/storage/LLM readiness |
| `POST /jobs` | Create orchestrator job |
| `GET /jobs/:id` | Read job status |
| `POST /documents/upload` | Upload CV/job file |
| `POST /rag/query` | Query RAG |
| `POST /match/candidate-job` | Candidate/job matching |

## CPU-only LLM Rules

Because no GPU is available:

- Use small models first
- Use queue-based async jobs
- Avoid long synchronous web requests
- Cache repeated answers
- Use deterministic scoring before LLM calls
- Use RAG context limits
- Use model timeout and retry rules

Recommended first model:

```bash
kubectl -n aia-dev exec deploy/aia-ollama-dev-cpu -- ollama pull llama3.2:3b
```

## Security Rules

The developer must not:

- Log CV content
- Log personal data unnecessarily
- Store secrets in code
- Call external LLMs without explicit config
- Expose internal services publicly
- Bypass job audit trail

## Definition of Done

A developer feature is done only when:

- Unit tests pass
- Docker image builds
- Health endpoint works
- Ready endpoint truthfully reports dependencies
- No secrets are exposed
- Job status is auditable
- Logs include request ID/job ID
- Deployment passes in `aia-dev`
