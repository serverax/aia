# AIA / OrdinoxAI Hiring API

FastAPI service exposing CRUD + AI candidate scoring over the `ordinoxai`
Postgres schema (`supabase/migrations/001_ordinoxai_aia_core_schema.sql`). It is
the data backbone the web frontend and the agent/worker services build on.

## Layout

```
apps/api/
├── main.py            # app factory, lifespan (DB pool + scorer), router wiring
├── config.py          # Settings (POSTGRES_*, ANTHROPIC_*, CORS) via env
├── tables.py          # whitelist of writable/filterable columns per table
├── db.py              # PgDatabase (asyncpg) + FakeDatabase (tests); audit writer
├── schemas.py         # Pydantic Create/Update/Read models per entity
├── scoring.py         # LLMScorer (Claude) + HeuristicScorer fallback
├── deps.py            # FastAPI dependencies (get_db, get_scorer)
├── routers/
│   ├── crud.py        # generic CRUD router factory + audit_event
│   ├── applications.py# CRUD + POST /applications/{id}/score
│   └── health.py      # /healthz, /readyz
└── tests/             # hermetic suite (FakeDatabase, no API key needed)
```

## Endpoints

| Resource | Path | Operations |
|----------|------|------------|
| Companies | `/companies` | list, create, get, patch, delete |
| Users | `/users` | list, create, get, patch, delete |
| Jobs | `/jobs` | list, create, get, patch, delete |
| Candidates | `/candidates` | list, create, get, patch, delete |
| Applications | `/applications` | list, create, get, patch, delete |
| Applications | `/applications/{id}/score` | **POST** — run AI scoring |
| Interviews | `/interviews` | list, create, get, patch, delete |
| Waitlist | `/waitlist` | list, create, get, patch, delete |
| Health | `/healthz`, `/readyz` | liveness / readiness |
| Meta | `/`, `/docs`, `/openapi.json` | service info + interactive docs |

List endpoints accept `limit` (1–200, default 50), `offset`, `order_by`,
`order_dir` (`asc`/`desc`), plus per-resource filters (e.g.
`/applications?job_id=…&status=submitted`, `/jobs?status=open`).

Every create/update/delete/score writes a row to `ordinoxai.audit_logs`.

## Configuration (environment)

| Var | Default | Notes |
|-----|---------|-------|
| `POSTGRES_HOST` / `POSTGRES_PORT` | `localhost` / `5432` | |
| `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` | `postgres` / `postgres` / *(empty)* | provided by the admin-created Secret in-cluster |
| `DB_SCHEMA` | `ordinoxai` | |
| `ANTHROPIC_API_KEY` | *(unset)* | when set, scoring uses Claude; otherwise the deterministic heuristic |
| `ANTHROPIC_MODEL` | `claude-sonnet-4-6` | |
| `CORS_ORIGINS` | *(empty)* | comma-separated origins for the web app |

No real secret has a default here — credentials come from the environment /
mounted Secret, never from source.

## Run locally

```bash
# from the repo root
pip install -r apps/api/requirements.txt
uvicorn apps.api.main:app --reload --port 8080
# docs: http://localhost:8080/docs
```

The app starts even if Postgres is unreachable; `/readyz` then reports `503`
while `/healthz` and `/docs` keep working.

## Tests

```bash
python -m pytest apps/api/tests -q
```

The suite is hermetic: it uses an in-memory `FakeDatabase` and the heuristic
scorer, so it needs neither a database nor an Anthropic API key.

## Docker

```bash
# build from the repo root (needs libs/ and root requirements.txt in context)
docker build -f apps/api/Dockerfile -t aia-hiring-api:0.1.0 .
docker run -p 8080:8080 --env-file .env aia-hiring-api:0.1.0
```

## Applying the schema

The `ordinoxai` schema is owned by the `supabase` namespace and applied by an
admin (per the handover, developers do not modify Supabase directly):

```bash
psql "$DATABASE_URL" -f supabase/migrations/001_ordinoxai_aia_core_schema.sql
```
