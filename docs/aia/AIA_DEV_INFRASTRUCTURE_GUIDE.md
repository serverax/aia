# AIA Hiring Webapp DEV Infrastructure Guide

## 1. Purpose

This document describes the DEV infrastructure for the AIA Hiring Webapp under:

- Protected production domain: `ordinoxai.com`
- DEV test domain: `dev.ordinoxai.com`
- DEV namespace: `aia-dev`

The infrastructure is designed to support:

- AI hiring workflows
- CV parsing
- job description processing
- candidate-job matching
- RAG document retrieval
- semantic search
- CPU-only LLM hosting
- object storage
- observability
- security baseline
- backup preparation
- CI/CD deployment

## 2. Safety Rules

The automation is dev-safe.

It must not:

- Delete Kubernetes objects
- Modify root `ordinoxai.com`
- Modify Cloudflare DNS automatically
- Use production namespaces
- Commit real secrets to Git
- Deploy to production without a separate production pipeline

Only this dev host should be used:

`dev.ordinoxai.com`

## 3. Namespaces

| Namespace | Purpose |
|---|---|
| `aia-dev` | Main AIA dev workloads |
| `aia-dev-storage` | MinIO S3-compatible object storage |
| `aia-dev-monitoring` | Monitoring configuration baseline |
| `aia-dev-security` | Security baseline configuration |

## 4. Supabase / Postgres Database

The schema file is:

`generated/supabase/aia_dev_schema.sql`

It creates three schemas:

| Schema | Purpose |
|---|---|
| `orchestrator_dev` | Jobs, job status, AI agent configuration, agent status |
| `rag_dev` | RAG documents, embeddings, queries, results |
| `semantic_dev` | Semantic indexes, documents, embeddings |

Required extensions:

- `pgcrypto`
- `vector`

### Orchestrator Tables

- `orchestrator_dev.jobs`
- `orchestrator_dev.job_status`
- `orchestrator_dev.agent_config`
- `orchestrator_dev.agent_status`

### RAG Tables

- `rag_dev.documents`
- `rag_dev.embeddings`
- `rag_dev.queries`
- `rag_dev.results`

### Semantic Search Tables

- `semantic_dev.indexes`
- `semantic_dev.documents`
- `semantic_dev.embeddings`

## 5. Storage

DEV storage uses MinIO:

- Deployment: `minio-dev`
- Namespace: `aia-dev-storage`
- Service: `minio-dev.aia-dev-storage.svc.cluster.local:9000`
- PVC: `minio-dev-data`
- Size: `25Gi`

Storage is intended for:

- CV uploads
- job description files
- extracted text artifacts
- generated reports
- temporary model artifacts
- backup exports

## 6. LLM Hosting Without GPU

DEV uses CPU-only Ollama:

- Deployment: `aia-ollama-dev-cpu`
- Namespace: `aia-dev`
- Service: `aia-ollama-dev-cpu.aia-dev.svc.cluster.local:11434`
- PVC: `ollama-dev-models`
- Size: `40Gi`

Recommended initial CPU models:

- `llama3.2:3b`
- `qwen2.5:3b`
- `phi3.5`

Do not start with large models on CPU. They will be slow.

## 7. Workers

Initial placeholder workers:

- `aia-orchestrator-dev-worker`
- `aia-rag-dev-worker`

These should later be replaced with real application images.

Expected future images:

- `ghcr.io/serverax/<repo>/aia-orchestrator-worker:dev-latest`
- `ghcr.io/serverax/<repo>/aia-rag-worker:dev-latest`
- `ghcr.io/serverax/<repo>/aia-search-worker:dev-latest`

## 8. Ingress

Ingress file:

`generated/k8s/70-ingress/aia-dev-ingress.yaml`

Target host:

`dev.ordinoxai.com`

Ingress class:

`traefik`

TLS issuer expected:

`letsencrypt-prod`

## 9. DNS

DNS is manual only.

Do not change root `ordinoxai.com`.

Only add:

| Type | Name | Value |
|---|---|---|
| A | dev | Ingress public IP |

Start with Cloudflare proxy disabled.

Then test:

```bash
dig +short dev.ordinoxai.com
curl -I https://dev.ordinoxai.com
```

## 10. CI/CD

Created workflows:

| Workflow | Purpose |
|---|---|
| `.github/workflows/aia-dev-ci.yml` | Validate scripts, manifests, and app build/tests |
| `.github/workflows/aia-dev-build-images.yml` | Build Docker images if Dockerfiles exist |
| `.github/workflows/aia-dev-deploy-k8s.yml` | Manual deployment to dev Kubernetes namespace |

## 11. GitHub Secrets Required

For deployment workflow:

| Secret | Purpose |
|---|---|
| `KUBE_CONFIG_B64` | Base64 kubeconfig for dev cluster deployment |
| `SUPABASE_DB_URL_DEV` | Optional DB URL for applying dev schema |

Create `KUBE_CONFIG_B64` locally:

```bash
base64 -w0 ~/.kube/config
```

Add it to GitHub:

`Settings > Secrets and variables > Actions > New repository secret`

## 12. Local Commands

Generate infra:

```bash
bash /mnt/f/aia-dev/scripts/aia-dev-full-infra-auto.sh
```

Apply infra:

```bash
APPLY_K8S=true bash /mnt/f/aia-dev/scripts/aia-dev-full-infra-auto.sh
```

Apply DB:

```bash
psql "$DATABASE_URL" -f /mnt/f/aia-dev/generated/supabase/aia_dev_schema.sql
```

Push to GitHub:

```bash
cd /mnt/f/aia-dev
BRANCH=dev COMMIT_MESSAGE="chore: add AIA dev infra" bash scripts/git-push-aia-dev.sh
```

Verify:

```bash
bash /mnt/f/aia-dev/scripts/verify-aia-dev-infra.sh
```

## 13. Current Status

Generated infrastructure requirements are covered as files/scripts:

| Area | Status |
|---|---|
| Supabase DB schema | Generated |
| Orchestrator DB | Generated |
| RAG DB | Generated |
| Semantic Search DB | Generated |
| Object storage | Generated |
| CPU-only LLM hosting | Generated |
| Workers | Generated as placeholders |
| Observability baseline | Generated |
| Security baseline | Generated |
| Backup CronJob placeholder | Generated |
| CI/CD pipelines | Generated |
| DNS guide | Generated, manual only |

Real runtime confirmation requires the verification script output and DB migration output.
