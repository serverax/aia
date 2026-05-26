#!/usr/bin/env bash
set -euo pipefail

# ==========================================================
# AIA Hiring Webapp DEV Infrastructure Automation
#
# SAFE BY DEFAULT:
# - No delete commands
# - No Cloudflare API mutation
# - No production namespace
# - No root ordinoxai.com changes
# - Generates manifests first
# - Applies only when APPLY_K8S=true
#
# Dry run:
#   bash /mnt/f/aia-dev/scripts/aia-dev-full-infra-auto.sh
#
# Apply to Kubernetes:
#   APPLY_K8S=true bash /mnt/f/aia-dev/scripts/aia-dev-full-infra-auto.sh
# ==========================================================

PROJECT_ROOT="${PROJECT_ROOT:-/mnt/f/aia-dev}"
OUT_DIR="${OUT_DIR:-${PROJECT_ROOT}/generated}"

PROD_DOMAIN="${PROD_DOMAIN:-ordinoxai.com}"
DEV_DOMAIN="${DEV_DOMAIN:-dev.ordinoxai.com}"

DEV_NS="${DEV_NS:-aia-dev}"
STORAGE_NS="${STORAGE_NS:-aia-dev-storage}"
MONITORING_NS="${MONITORING_NS:-aia-dev-monitoring}"
SECURITY_NS="${SECURITY_NS:-aia-dev-security}"

APPLY_K8S="${APPLY_K8S:-false}"

echo "=================================================="
echo "AIA Hiring Webapp DEV Infrastructure Generator"
echo "Project root:       ${PROJECT_ROOT}"
echo "Output dir:         ${OUT_DIR}"
echo "Protected domain:   ${PROD_DOMAIN}"
echo "Dev domain:         ${DEV_DOMAIN}"
echo "Dev namespace:      ${DEV_NS}"
echo "Storage namespace:  ${STORAGE_NS}"
echo "Monitoring ns:      ${MONITORING_NS}"
echo "Security ns:        ${SECURITY_NS}"
echo "Apply K8s:          ${APPLY_K8S}"
echo "=================================================="

# ==========================================================
# Hard safety checks
# ==========================================================

if [[ "${PROJECT_ROOT}" != "/mnt/f/aia" && "${PROJECT_ROOT}" != "/mnt/f/aia-dev" ]]; then
  echo "ERROR: PROJECT_ROOT must be /mnt/f/aia or /mnt/f/aia-dev for this dev script."
  exit 1
fi

if [[ "${DEV_DOMAIN}" == "${PROD_DOMAIN}" ]]; then
  echo "ERROR: DEV_DOMAIN cannot equal PROD_DOMAIN."
  exit 1
fi

if [[ "${DEV_NS}" == *prod* || "${STORAGE_NS}" == *prod* || "${MONITORING_NS}" == *prod* || "${SECURITY_NS}" == *prod* ]]; then
  echo "ERROR: one namespace contains 'prod'. Refusing."
  exit 1
fi

# ==========================================================
# Create directories
# ==========================================================

mkdir -p \
  "${OUT_DIR}/supabase" \
  "${OUT_DIR}/k8s/00-namespaces" \
  "${OUT_DIR}/k8s/10-storage" \
  "${OUT_DIR}/k8s/20-llm" \
  "${OUT_DIR}/k8s/30-workers" \
  "${OUT_DIR}/k8s/40-backup" \
  "${OUT_DIR}/k8s/50-monitoring" \
  "${OUT_DIR}/k8s/60-security" \
  "${OUT_DIR}/k8s/70-ingress" \
  "${OUT_DIR}/dns" \
  "${OUT_DIR}/docs"

# ==========================================================
# 1. Supabase database schema
# ==========================================================

cat > "${OUT_DIR}/supabase/aia_dev_schema.sql" <<'SQL'
-- ==========================================================
-- AIA Hiring Webapp DEV Supabase Schema
-- Schemas:
--   orchestrator_dev
--   rag_dev
--   semantic_dev
-- ==========================================================

create extension if not exists pgcrypto;
create extension if not exists vector;

create schema if not exists orchestrator_dev;
create schema if not exists rag_dev;
create schema if not exists semantic_dev;

create or replace function public.aia_set_updated_at()
returns trigger
language plpgsql
set search_path = public
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

-- ==========================================================
-- Orchestrator Service DB
-- ==========================================================

create table if not exists orchestrator_dev.jobs (
  id uuid primary key default gen_random_uuid(),
  type text not null,
  payload jsonb not null default '{}'::jsonb,
  status text not null default 'queued',
  priority int not null default 5,
  attempts int not null default 0,
  max_attempts int not null default 3,
  locked_by text,
  locked_at timestamptz,
  scheduled_at timestamptz not null default now(),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists orchestrator_dev.job_status (
  id uuid primary key default gen_random_uuid(),
  job_id uuid not null references orchestrator_dev.jobs(id) on delete cascade,
  status text not null,
  message text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists orchestrator_dev.agent_config (
  id uuid primary key default gen_random_uuid(),
  name text not null unique,
  type text not null,
  config jsonb not null default '{}'::jsonb,
  enabled boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists orchestrator_dev.agent_status (
  id uuid primary key default gen_random_uuid(),
  agent_id uuid not null references orchestrator_dev.agent_config(id) on delete cascade,
  status text not null,
  last_seen timestamptz,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_orch_dev_jobs_type on orchestrator_dev.jobs(type);
create index if not exists idx_orch_dev_jobs_status on orchestrator_dev.jobs(status);
create index if not exists idx_orch_dev_jobs_scheduled_at on orchestrator_dev.jobs(scheduled_at);
create index if not exists idx_orch_dev_job_status_job_id on orchestrator_dev.job_status(job_id);
create index if not exists idx_orch_dev_agent_status_agent_id on orchestrator_dev.agent_status(agent_id);

drop trigger if exists trg_orch_dev_jobs_updated_at on orchestrator_dev.jobs;
create trigger trg_orch_dev_jobs_updated_at
before update on orchestrator_dev.jobs
for each row execute function public.aia_set_updated_at();

drop trigger if exists trg_orch_dev_job_status_updated_at on orchestrator_dev.job_status;
create trigger trg_orch_dev_job_status_updated_at
before update on orchestrator_dev.job_status
for each row execute function public.aia_set_updated_at();

drop trigger if exists trg_orch_dev_agent_config_updated_at on orchestrator_dev.agent_config;
create trigger trg_orch_dev_agent_config_updated_at
before update on orchestrator_dev.agent_config
for each row execute function public.aia_set_updated_at();

drop trigger if exists trg_orch_dev_agent_status_updated_at on orchestrator_dev.agent_status;
create trigger trg_orch_dev_agent_status_updated_at
before update on orchestrator_dev.agent_status
for each row execute function public.aia_set_updated_at();

-- ==========================================================
-- RAG Service DB
-- ==========================================================

create table if not exists rag_dev.documents (
  id uuid primary key default gen_random_uuid(),
  source text not null,
  content text not null,
  metadata jsonb not null default '{}'::jsonb,
  content_hash text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists rag_dev.embeddings (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references rag_dev.documents(id) on delete cascade,
  embedding vector(1536),
  model text not null default 'text-embedding-3-small',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists rag_dev.queries (
  id uuid primary key default gen_random_uuid(),
  query text not null,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists rag_dev.results (
  id uuid primary key default gen_random_uuid(),
  query_id uuid not null references rag_dev.queries(id) on delete cascade,
  document_id uuid not null references rag_dev.documents(id) on delete cascade,
  score double precision not null,
  created_at timestamptz not null default now()
);

create index if not exists idx_rag_dev_documents_source on rag_dev.documents(source);
create index if not exists idx_rag_dev_documents_metadata on rag_dev.documents using gin(metadata);
create index if not exists idx_rag_dev_documents_hash on rag_dev.documents(content_hash);
create index if not exists idx_rag_dev_embeddings_document_id on rag_dev.embeddings(document_id);
create index if not exists idx_rag_dev_results_query_id on rag_dev.results(query_id);
create index if not exists idx_rag_dev_results_document_id on rag_dev.results(document_id);

-- Enable later when enough rows exist:
-- create index if not exists idx_rag_dev_embeddings_hnsw
--   on rag_dev.embeddings using hnsw (embedding vector_cosine_ops);

drop trigger if exists trg_rag_dev_documents_updated_at on rag_dev.documents;
create trigger trg_rag_dev_documents_updated_at
before update on rag_dev.documents
for each row execute function public.aia_set_updated_at();

drop trigger if exists trg_rag_dev_embeddings_updated_at on rag_dev.embeddings;
create trigger trg_rag_dev_embeddings_updated_at
before update on rag_dev.embeddings
for each row execute function public.aia_set_updated_at();

-- ==========================================================
-- Semantic Search Service DB
-- ==========================================================

create table if not exists semantic_dev.indexes (
  id uuid primary key default gen_random_uuid(),
  name text not null unique,
  description text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists semantic_dev.documents (
  id uuid primary key default gen_random_uuid(),
  index_id uuid references semantic_dev.indexes(id) on delete cascade,
  source text not null,
  content text not null,
  metadata jsonb not null default '{}'::jsonb,
  content_hash text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists semantic_dev.embeddings (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references semantic_dev.documents(id) on delete cascade,
  embedding vector(1536),
  model text not null default 'text-embedding-3-small',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_semantic_dev_indexes_name on semantic_dev.indexes(name);
create index if not exists idx_semantic_dev_documents_index_id on semantic_dev.documents(index_id);
create index if not exists idx_semantic_dev_documents_source on semantic_dev.documents(source);
create index if not exists idx_semantic_dev_documents_metadata on semantic_dev.documents using gin(metadata);
create index if not exists idx_semantic_dev_documents_hash on semantic_dev.documents(content_hash);
create index if not exists idx_semantic_dev_embeddings_document_id on semantic_dev.embeddings(document_id);

-- Enable later when enough rows exist:
-- create index if not exists idx_semantic_dev_embeddings_hnsw
--   on semantic_dev.embeddings using hnsw (embedding vector_cosine_ops);

drop trigger if exists trg_semantic_dev_indexes_updated_at on semantic_dev.indexes;
create trigger trg_semantic_dev_indexes_updated_at
before update on semantic_dev.indexes
for each row execute function public.aia_set_updated_at();

drop trigger if exists trg_semantic_dev_documents_updated_at on semantic_dev.documents;
create trigger trg_semantic_dev_documents_updated_at
before update on semantic_dev.documents
for each row execute function public.aia_set_updated_at();

drop trigger if exists trg_semantic_dev_embeddings_updated_at on semantic_dev.embeddings;
create trigger trg_semantic_dev_embeddings_updated_at
before update on semantic_dev.embeddings
for each row execute function public.aia_set_updated_at();

insert into semantic_dev.indexes(name, description, metadata)
values
  ('candidate-cv-dev-index', 'DEV index for candidate CVs', '{"env":"dev","type":"candidate"}'),
  ('job-description-dev-index', 'DEV index for job descriptions', '{"env":"dev","type":"job"}'),
  ('interview-qa-dev-index', 'DEV index for interview questions and answers', '{"env":"dev","type":"interview"}')
on conflict (name) do nothing;
SQL

# ==========================================================
# 2. Kubernetes namespaces
# ==========================================================

cat > "${OUT_DIR}/k8s/00-namespaces/namespaces.yaml" <<YAML
apiVersion: v1
kind: Namespace
metadata:
  name: ${DEV_NS}
  labels:
    app.kubernetes.io/part-of: aia-hiring-dev
    environment: dev
    pod-security.kubernetes.io/enforce: baseline
    pod-security.kubernetes.io/audit: baseline
    pod-security.kubernetes.io/warn: baseline
---
apiVersion: v1
kind: Namespace
metadata:
  name: ${STORAGE_NS}
  labels:
    app.kubernetes.io/part-of: aia-hiring-dev
    environment: dev
    pod-security.kubernetes.io/enforce: baseline
    pod-security.kubernetes.io/audit: baseline
    pod-security.kubernetes.io/warn: baseline
---
apiVersion: v1
kind: Namespace
metadata:
  name: ${MONITORING_NS}
  labels:
    app.kubernetes.io/part-of: aia-hiring-dev
    environment: dev
    pod-security.kubernetes.io/enforce: baseline
    pod-security.kubernetes.io/audit: baseline
    pod-security.kubernetes.io/warn: baseline
---
apiVersion: v1
kind: Namespace
metadata:
  name: ${SECURITY_NS}
  labels:
    app.kubernetes.io/part-of: aia-hiring-dev
    environment: dev
    pod-security.kubernetes.io/enforce: baseline
    pod-security.kubernetes.io/audit: baseline
    pod-security.kubernetes.io/warn: baseline
YAML

# ==========================================================
# 3. S3-compatible storage: MinIO DEV
# ==========================================================

MINIO_DEV_USER="${MINIO_DEV_USER:-aia_dev_minio}"
MINIO_DEV_PASSWORD="${MINIO_DEV_PASSWORD:-$(openssl rand -base64 32 | tr -d '\n')}"

cat > "${OUT_DIR}/secrets.dev.env" <<SECRETS
# DEV ONLY - do not commit
MINIO_DEV_USER=${MINIO_DEV_USER}
MINIO_DEV_PASSWORD=${MINIO_DEV_PASSWORD}
SECRETS

chmod 600 "${OUT_DIR}/secrets.dev.env"

cat > "${OUT_DIR}/k8s/10-storage/minio-dev.yaml" <<YAML
apiVersion: v1
kind: Secret
metadata:
  name: minio-dev-root-secret
  namespace: ${STORAGE_NS}
type: Opaque
stringData:
  MINIO_ROOT_USER: "${MINIO_DEV_USER}"
  MINIO_ROOT_PASSWORD: "${MINIO_DEV_PASSWORD}"
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: minio-dev-data
  namespace: ${STORAGE_NS}
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 25Gi
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: minio-dev
  namespace: ${STORAGE_NS}
  labels:
    app: minio-dev
spec:
  replicas: 1
  selector:
    matchLabels:
      app: minio-dev
  template:
    metadata:
      labels:
        app: minio-dev
        environment: dev
    spec:
      securityContext:
        fsGroup: 1000
      containers:
        - name: minio
          image: quay.io/minio/minio:RELEASE.2025-04-22T22-12-26Z
          args:
            - server
            - /data
            - --console-address
            - ":9001"
          envFrom:
            - secretRef:
                name: minio-dev-root-secret
          ports:
            - name: s3
              containerPort: 9000
            - name: console
              containerPort: 9001
          resources:
            requests:
              cpu: "250m"
              memory: "512Mi"
            limits:
              cpu: "1"
              memory: "2Gi"
          volumeMounts:
            - name: data
              mountPath: /data
          securityContext:
            allowPrivilegeEscalation: false
            capabilities:
              drop:
                - ALL
      volumes:
        - name: data
          persistentVolumeClaim:
            claimName: minio-dev-data
---
apiVersion: v1
kind: Service
metadata:
  name: minio-dev
  namespace: ${STORAGE_NS}
spec:
  selector:
    app: minio-dev
  ports:
    - name: s3
      port: 9000
      targetPort: 9000
    - name: console
      port: 9001
      targetPort: 9001
YAML

# ==========================================================
# 4. CPU-only LLM: Ollama DEV
# ==========================================================

cat > "${OUT_DIR}/k8s/20-llm/ollama-dev-cpu.yaml" <<YAML
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: ollama-dev-models
  namespace: ${DEV_NS}
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 40Gi
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: aia-ollama-dev-cpu
  namespace: ${DEV_NS}
  labels:
    app: aia-ollama-dev-cpu
spec:
  replicas: 1
  selector:
    matchLabels:
      app: aia-ollama-dev-cpu
  template:
    metadata:
      labels:
        app: aia-ollama-dev-cpu
        environment: dev
    spec:
      containers:
        - name: ollama
          image: ollama/ollama:0.6.8
          ports:
            - name: http
              containerPort: 11434
          env:
            - name: OLLAMA_NUM_PARALLEL
              value: "1"
            - name: OLLAMA_MAX_LOADED_MODELS
              value: "1"
            - name: OLLAMA_KEEP_ALIVE
              value: "5m"
          resources:
            requests:
              cpu: "2"
              memory: "4Gi"
            limits:
              cpu: "8"
              memory: "16Gi"
          volumeMounts:
            - name: models
              mountPath: /root/.ollama
      volumes:
        - name: models
          persistentVolumeClaim:
            claimName: ollama-dev-models
---
apiVersion: v1
kind: Service
metadata:
  name: aia-ollama-dev-cpu
  namespace: ${DEV_NS}
spec:
  selector:
    app: aia-ollama-dev-cpu
  ports:
    - name: http
      port: 11434
      targetPort: 11434
YAML

# ==========================================================
# 5. Workers placeholders
# ==========================================================

cat > "${OUT_DIR}/k8s/30-workers/aia-dev-workers.yaml" <<YAML
apiVersion: apps/v1
kind: Deployment
metadata:
  name: aia-orchestrator-dev-worker
  namespace: ${DEV_NS}
  labels:
    app: aia-orchestrator-dev-worker
spec:
  replicas: 1
  selector:
    matchLabels:
      app: aia-orchestrator-dev-worker
  template:
    metadata:
      labels:
        app: aia-orchestrator-dev-worker
        environment: dev
    spec:
      containers:
        - name: worker
          image: nginx:1.27.5-alpine
          command:
            - /bin/sh
            - -c
            - |
              echo "AIA orchestrator worker placeholder running";
              while true; do sleep 3600; done
          env:
            - name: ENVIRONMENT
              value: "dev"
            - name: OLLAMA_BASE_URL
              value: "http://aia-ollama-dev-cpu.${DEV_NS}.svc.cluster.local:11434"
            - name: STORAGE_ENDPOINT
              value: "http://minio-dev.${STORAGE_NS}.svc.cluster.local:9000"
          resources:
            requests:
              cpu: "100m"
              memory: "128Mi"
            limits:
              cpu: "500m"
              memory: "512Mi"
          securityContext:
            allowPrivilegeEscalation: false
            capabilities:
              drop:
                - ALL
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: aia-rag-dev-worker
  namespace: ${DEV_NS}
  labels:
    app: aia-rag-dev-worker
spec:
  replicas: 1
  selector:
    matchLabels:
      app: aia-rag-dev-worker
  template:
    metadata:
      labels:
        app: aia-rag-dev-worker
        environment: dev
    spec:
      containers:
        - name: worker
          image: nginx:1.27.5-alpine
          command:
            - /bin/sh
            - -c
            - |
              echo "AIA RAG worker placeholder running";
              while true; do sleep 3600; done
          env:
            - name: ENVIRONMENT
              value: "dev"
            - name: STORAGE_ENDPOINT
              value: "http://minio-dev.${STORAGE_NS}.svc.cluster.local:9000"
          resources:
            requests:
              cpu: "100m"
              memory: "128Mi"
            limits:
              cpu: "500m"
              memory: "512Mi"
          securityContext:
            allowPrivilegeEscalation: false
            capabilities:
              drop:
                - ALL
YAML

# ==========================================================
# 6. Backup CronJob placeholder
# ==========================================================

cat > "${OUT_DIR}/k8s/40-backup/supabase-dev-backup-cronjob.yaml" <<YAML
apiVersion: batch/v1
kind: CronJob
metadata:
  name: aia-supabase-dev-backup
  namespace: ${DEV_NS}
spec:
  schedule: "15 2 * * *"
  successfulJobsHistoryLimit: 3
  failedJobsHistoryLimit: 3
  suspend: true
  jobTemplate:
    spec:
      template:
        spec:
          restartPolicy: OnFailure
          containers:
            - name: backup
              image: postgres:16-alpine
              command:
                - /bin/sh
                - -c
                - |
                  set -eu
                  echo "DEV backup placeholder."
                  echo "Set DATABASE_URL and S3 upload command before enabling."
                  exit 0
              resources:
                requests:
                  cpu: "100m"
                  memory: "128Mi"
                limits:
                  cpu: "500m"
                  memory: "512Mi"
YAML

# ==========================================================
# 7. Monitoring baseline
# ==========================================================

cat > "${OUT_DIR}/k8s/50-monitoring/aia-dev-monitoring-config.yaml" <<YAML
apiVersion: v1
kind: ConfigMap
metadata:
  name: aia-dev-monitoring-baseline
  namespace: ${MONITORING_NS}
data:
  metrics.md: |
    Required metrics:
    - HTTP request latency
    - HTTP error rate
    - Worker queue depth
    - Job failure count
    - Supabase query latency
    - Vector search latency
    - LLM request duration
    - LLM token throughput
    - MinIO bucket usage
    - CPU usage
    - Memory usage
    - Pod restarts

  alerts.md: |
    Required alerts:
    - API 5xx > 5% for 5 minutes
    - LLM latency > 30 seconds p95
    - Worker queue older than 10 minutes
    - Database CPU > 80%
    - Storage usage > 80%
    - Backup failure
    - Pod restart loop
    - Certificate expiry below 14 days

  stack.md: |
    Recommended stack:
    - Prometheus
    - Grafana
    - Loki
    - Promtail or Fluent Bit
    - Jaeger or OpenTelemetry Collector
YAML

# ==========================================================
# 8. Security baseline
# ==========================================================

cat > "${OUT_DIR}/k8s/60-security/network-policies-dev.yaml" <<YAML
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: aia-dev-default-deny-ingress
  namespace: ${DEV_NS}
spec:
  podSelector: {}
  policyTypes:
    - Ingress
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: aia-dev-allow-same-project
  namespace: ${DEV_NS}
spec:
  podSelector: {}
  policyTypes:
    - Ingress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              app.kubernetes.io/part-of: aia-hiring-dev
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: aia-dev-storage-default-deny-ingress
  namespace: ${STORAGE_NS}
spec:
  podSelector: {}
  policyTypes:
    - Ingress
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: aia-dev-allow-minio-from-project
  namespace: ${STORAGE_NS}
spec:
  podSelector:
    matchLabels:
      app: minio-dev
  policyTypes:
    - Ingress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              app.kubernetes.io/part-of: aia-hiring-dev
      ports:
        - protocol: TCP
          port: 9000
        - protocol: TCP
          port: 9001
YAML

cat > "${OUT_DIR}/k8s/60-security/aia-dev-security-baseline.yaml" <<YAML
apiVersion: v1
kind: ConfigMap
metadata:
  name: aia-dev-security-baseline
  namespace: ${SECURITY_NS}
data:
  policy.md: |
    Security requirements:
    - No production DNS mutation from automation
    - No root ordinoxai.com changes from dev scripts
    - No secret values committed to Git
    - No :latest images in production
    - Containers must drop Linux capabilities
    - No privileged containers
    - Use NetworkPolicy between services
    - Scan containers with Trivy before production
    - Use sealed-secrets, Vault, or external secret operator for real secrets
    - Backups must be encrypted
    - Access logs must not expose CV contents or personal data
YAML

# ==========================================================
# 9. DEV placeholder webapp and ingress
# ==========================================================

cat > "${OUT_DIR}/k8s/70-ingress/aia-dev-placeholder-web.yaml" <<YAML
apiVersion: v1
kind: ConfigMap
metadata:
  name: aia-dev-placeholder-html
  namespace: ${DEV_NS}
data:
  index.html: |
    <!doctype html>
    <html>
      <head>
        <title>AIA DEV</title>
        <meta charset="utf-8" />
      </head>
      <body style="font-family: Arial, sans-serif; padding: 40px;">
        <h1>AIA Hiring Webapp DEV</h1>
        <p>Status: running</p>
        <p>Domain: ${DEV_DOMAIN}</p>
        <p>Protected production domain: ${PROD_DOMAIN}</p>
        <p>This is a dev placeholder and does not modify production DNS.</p>
      </body>
    </html>
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: aia-dev-web
  namespace: ${DEV_NS}
  labels:
    app: aia-dev-web
spec:
  replicas: 1
  selector:
    matchLabels:
      app: aia-dev-web
  template:
    metadata:
      labels:
        app: aia-dev-web
        environment: dev
    spec:
      containers:
        - name: web
          image: nginx:1.27.5-alpine
          ports:
            - name: http
              containerPort: 80
          volumeMounts:
            - name: html
              mountPath: /usr/share/nginx/html
          resources:
            requests:
              cpu: "50m"
              memory: "64Mi"
            limits:
              cpu: "250m"
              memory: "256Mi"
          securityContext:
            allowPrivilegeEscalation: false
            capabilities:
              drop:
                - ALL
      volumes:
        - name: html
          configMap:
            name: aia-dev-placeholder-html
---
apiVersion: v1
kind: Service
metadata:
  name: aia-dev-web
  namespace: ${DEV_NS}
spec:
  selector:
    app: aia-dev-web
  ports:
    - name: http
      port: 80
      targetPort: 80
YAML

cat > "${OUT_DIR}/k8s/70-ingress/aia-dev-ingress.yaml" <<YAML
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: aia-dev-ingress
  namespace: ${DEV_NS}
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  ingressClassName: traefik
  tls:
    - hosts:
        - ${DEV_DOMAIN}
      secretName: aia-dev-tls
  rules:
    - host: ${DEV_DOMAIN}
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: aia-dev-web
                port:
                  number: 80
YAML

# ==========================================================
# 10. Manual DNS guide
# ==========================================================

cat > "${OUT_DIR}/dns/cloudflare-dev-dns-manual.md" <<DNS
# Cloudflare DNS Manual Step

This script does NOT call Cloudflare API.

Protected production domain:

- ${PROD_DOMAIN}

Dev domain:

- ${DEV_DOMAIN}

Do NOT delete or edit existing production records.

Add only this record manually after ingress IP is confirmed:

Type: A
Name: dev
Value: <INGRESS_PUBLIC_IP>
Proxy: DNS only first
TTL: Auto

After HTTPS works, you may enable Cloudflare proxy.

Validation:

dig +short ${DEV_DOMAIN}
curl -I https://${DEV_DOMAIN}

Rollback:

Only remove the dev record if needed.
Do not touch:
- root ${PROD_DOMAIN}
- www
- api
- mail
- MX
- TXT
- SPF
- DKIM
- DMARC
DNS

# ==========================================================
# 11. Operator guide
# ==========================================================

cat > "${OUT_DIR}/docs/README_NEXT_STEPS.md" <<DOC
# AIA DEV Infrastructure Next Steps

Generated by:

\${PROJECT_ROOT}/scripts/aia-dev-full-infra-auto.sh

## Safe dry run

bash /mnt/f/aia-dev/scripts/aia-dev-full-infra-auto.sh

## Edit MinIO secret before apply

File:

/mnt/f/aia-dev/generated/k8s/10-storage/minio-dev.yaml

Replace:

CHANGE_ME_DEV_MINIO_USER
CHANGE_ME_DEV_MINIO_PASSWORD

## Apply Kubernetes manifests

APPLY_K8S=true bash /mnt/f/aia-dev/scripts/aia-dev-full-infra-auto.sh

## Apply Supabase schema manually

psql "\$DATABASE_URL" -f /mnt/f/aia-dev/generated/supabase/aia_dev_schema.sql

## Check pods

kubectl -n aia-dev get pods -o wide
kubectl -n aia-dev-storage get pods -o wide
kubectl -n aia-dev get svc
kubectl -n aia-dev get ingress -o wide

## Pull small CPU model after Ollama is running

kubectl -n aia-dev exec deploy/aia-ollama-dev-cpu -- ollama pull llama3.2:3b

## Test Ollama internally

kubectl -n aia-dev run curl-test --rm -it --image=curlimages/curl:8.10.1 --restart=Never -- \
  curl -s http://aia-ollama-dev-cpu.aia-dev.svc.cluster.local:11434/api/tags

## DNS

Manual only. Add dev.ordinoxai.com as A record to ingress IP.
DOC

# ==========================================================
# 12. Print generated files
# ==========================================================

echo ""
echo "Generated files:"
find "${OUT_DIR}" -type f | sort

echo ""
echo "Safety scan:"
if grep -R "kubectl delete\|cloudflare\|curl.*api.cloudflare\|cf_api\|CF_API" "${PROJECT_ROOT}/scripts" "${OUT_DIR}" 2>/dev/null; then
  echo "WARNING: Found risky text. Review above."
else
  echo "PASS: no kubectl delete or Cloudflare API mutation found."
fi

if grep -R "ordinoxai.com" "${OUT_DIR}/k8s" 2>/dev/null | grep -v "dev.ordinoxai.com"; then
  echo "WARNING: production domain found in K8s manifests."
else
  echo "PASS: production root domain not used in K8s ingress."
fi

echo ""
echo "Dry-run generation complete."

# ==========================================================
# 13. Optional Kubernetes apply
# ==========================================================

if [[ "${APPLY_K8S}" == "true" ]]; then
  echo ""
  echo "APPLY_K8S=true detected."

  if ! command -v kubectl >/dev/null 2>&1; then
    echo "ERROR: kubectl not found."
    exit 1
  fi

  echo ""
  echo "Current Kubernetes context:"
  kubectl config current-context || true

  echo ""
  echo "Checking generated manifests for unresolved placeholders..."
  if grep -R "CHANGE_ME" "${OUT_DIR}/k8s"; then
    echo "ERROR: unresolved CHANGE_ME placeholder found."
    exit 1
  fi

  echo ""
  echo "Applying DEV namespaces..."
  kubectl apply -f "${OUT_DIR}/k8s/00-namespaces/namespaces.yaml"

  echo ""
  echo "Applying DEV storage..."
  kubectl apply -f "${OUT_DIR}/k8s/10-storage/minio-dev.yaml"

  echo ""
  echo "Applying DEV CPU LLM..."
  kubectl apply -f "${OUT_DIR}/k8s/20-llm/ollama-dev-cpu.yaml"

  echo ""
  echo "Applying DEV workers..."
  kubectl apply -f "${OUT_DIR}/k8s/30-workers/aia-dev-workers.yaml"

  echo ""
  echo "Applying DEV backup placeholder..."
  kubectl apply -f "${OUT_DIR}/k8s/40-backup/supabase-dev-backup-cronjob.yaml"

  echo ""
  echo "Applying DEV monitoring config..."
  kubectl apply -f "${OUT_DIR}/k8s/50-monitoring/aia-dev-monitoring-config.yaml"

  echo ""
  echo "Applying DEV security..."
  kubectl apply -f "${OUT_DIR}/k8s/60-security/network-policies-dev.yaml"
  kubectl apply -f "${OUT_DIR}/k8s/60-security/aia-dev-security-baseline.yaml"

  echo ""
  echo "Applying DEV web and ingress..."
  kubectl apply -f "${OUT_DIR}/k8s/70-ingress/aia-dev-placeholder-web.yaml"
  kubectl apply -f "${OUT_DIR}/k8s/70-ingress/aia-dev-ingress.yaml"

  echo ""
  echo "Rollout checks:"
  kubectl -n "${DEV_NS}" rollout status deploy/aia-dev-web --timeout=120s || true
  kubectl -n "${DEV_NS}" rollout status deploy/aia-ollama-dev-cpu --timeout=180s || true
  kubectl -n "${DEV_NS}" rollout status deploy/aia-orchestrator-dev-worker --timeout=120s || true
  kubectl -n "${DEV_NS}" rollout status deploy/aia-rag-dev-worker --timeout=120s || true
  kubectl -n "${STORAGE_NS}" rollout status deploy/minio-dev --timeout=180s || true

  echo ""
  echo "DEV pods:"
  kubectl -n "${DEV_NS}" get pods -o wide
  kubectl -n "${STORAGE_NS}" get pods -o wide

  echo ""
  echo "DEV services:"
  kubectl -n "${DEV_NS}" get svc
  kubectl -n "${STORAGE_NS}" get svc

  echo ""
  echo "DEV ingress:"
  kubectl -n "${DEV_NS}" get ingress -o wide || true
fi

echo ""
echo "Done."
echo ""
echo "Next commands:"
echo "  ls -la ${OUT_DIR}"
echo "  find ${OUT_DIR} -type f | sort"
echo ""
echo "Apply Supabase manually:"
echo "  psql \"\$DATABASE_URL\" -f ${OUT_DIR}/supabase/aia_dev_schema.sql"
echo ""
echo "DNS guide:"
echo "  cat ${OUT_DIR}/dns/cloudflare-dev-dns-manual.md"
