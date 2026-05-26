#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${PROJECT_ROOT:-/mnt/f/aia-dev}"
OUT_DIR="${OUT_DIR:-${PROJECT_ROOT}/generated}"

DEV_NS="${DEV_NS:-aia-dev}"
STORAGE_NS="${STORAGE_NS:-aia-dev-storage}"
MONITORING_NS="${MONITORING_NS:-aia-dev-monitoring}"
SECURITY_NS="${SECURITY_NS:-aia-dev-security}"

PROD_DOMAIN="${PROD_DOMAIN:-ordinoxai.com}"
DEV_DOMAIN="${DEV_DOMAIN:-dev.ordinoxai.com}"

RUN_GIT_PUSH="${RUN_GIT_PUSH:-false}"
GIT_COMMIT_MESSAGE="${GIT_COMMIT_MESSAGE:-chore: add AIA dev infrastructure CI/CD and handover docs}"

echo "=================================================="
echo "AIA DEV CI/CD + Docs Automation"
echo "Project root: ${PROJECT_ROOT}"
echo "Output dir:   ${OUT_DIR}"
echo "Dev ns:       ${DEV_NS}"
echo "Dev domain:   ${DEV_DOMAIN}"
echo "Protected:    ${PROD_DOMAIN}"
echo "Git push:     ${RUN_GIT_PUSH}"
echo "=================================================="

if [[ "${PROJECT_ROOT}" != "/mnt/f/aia-dev" ]]; then
  echo "ERROR: PROJECT_ROOT must be /mnt/f/aia-dev"
  exit 1
fi

if [[ "${DEV_DOMAIN}" == "${PROD_DOMAIN}" ]]; then
  echo "ERROR: DEV_DOMAIN cannot equal PROD_DOMAIN"
  exit 1
fi

if [[ "${DEV_NS}" == *prod* || "${STORAGE_NS}" == *prod* || "${MONITORING_NS}" == *prod* || "${SECURITY_NS}" == *prod* ]]; then
  echo "ERROR: namespace contains prod. Refusing."
  exit 1
fi

mkdir -p \
  "${PROJECT_ROOT}/.github/workflows" \
  "${PROJECT_ROOT}/scripts" \
  "${PROJECT_ROOT}/docs/aia" \
  "${OUT_DIR}/evidence"

# ==========================================================
# 1. GitHub Actions CI
# ==========================================================

cat > "${PROJECT_ROOT}/.github/workflows/aia-dev-ci.yml" <<'YAML'
name: AIA Dev CI

on:
  push:
    branches:
      - main
      - master
      - dev
    paths:
      - "**"
      - ".github/workflows/aia-dev-ci.yml"
  pull_request:
    branches:
      - main
      - master
      - dev

permissions:
  contents: read

jobs:
  validate:
    name: Validate project
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Show repository
        run: |
          echo "Repository: $GITHUB_REPOSITORY"
          echo "Branch: $GITHUB_REF_NAME"

      - name: Validate shell scripts
        run: |
          set -e
          find scripts -type f -name "*.sh" -print0 2>/dev/null | xargs -0 -r bash -n
          echo "Shell syntax validation passed"

      - name: Validate Kubernetes YAML exists
        run: |
          set -e
          if [ -d "generated/k8s" ]; then
            find generated/k8s -type f -name "*.yaml" -print
          else
            echo "generated/k8s not found yet. Run the infra generator first."
          fi

      - name: Node install and test if package.json exists
        run: |
          set -e
          if [ -f package.json ]; then
            corepack enable || true
            if [ -f pnpm-lock.yaml ]; then
              pnpm install --frozen-lockfile
              pnpm test --if-present
              pnpm run build --if-present
            elif [ -f yarn.lock ]; then
              yarn install --frozen-lockfile
              yarn test --if-present
              yarn build --if-present
            else
              npm ci
              npm test --if-present
              npm run build --if-present
            fi
          else
            echo "No package.json found. Skipping Node tests."
          fi

      - name: Safety scan
        run: |
          set -e
          echo "Checking for risky operations..."
          if grep -R "kubectl delete\|curl.*api.cloudflare\|CF_API_TOKEN\|cloudflare.com/client/v4" . \
            --exclude-dir=.git \
            --exclude="aia-dev-cicd-docs-auto.sh" \
            --exclude="cloudflare-dev-dns-manual.md"; then
            echo "Risky text found. Review before deployment."
            exit 1
          fi
          echo "Safety scan passed"
YAML

# ==========================================================
# 2. GitHub Actions build workflow
# ==========================================================

cat > "${PROJECT_ROOT}/.github/workflows/aia-dev-build-images.yml" <<'YAML'
name: AIA Dev Build Images

on:
  workflow_dispatch:
  push:
    branches:
      - main
      - master
      - dev
    paths:
      - "apps/**"
      - "services/**"
      - "Dockerfile"
      - ".github/workflows/aia-dev-build-images.yml"

permissions:
  contents: read
  packages: write

jobs:
  build:
    name: Build available Docker images
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Login to GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Detect and build images
        shell: bash
        run: |
          set -euo pipefail

          OWNER_REPO="$(echo "${GITHUB_REPOSITORY}" | tr '[:upper:]' '[:lower:]')"
          SHORT_SHA="${GITHUB_SHA::7}"

          build_if_exists() {
            local name="$1"
            local dockerfile="$2"
            local context="$3"

            if [ -f "$dockerfile" ]; then
              echo "Building $name from $dockerfile"
              docker build \
                -f "$dockerfile" \
                -t "ghcr.io/${OWNER_REPO}/${name}:dev-${SHORT_SHA}" \
                -t "ghcr.io/${OWNER_REPO}/${name}:dev-latest" \
                "$context"

              docker push "ghcr.io/${OWNER_REPO}/${name}:dev-${SHORT_SHA}"
              docker push "ghcr.io/${OWNER_REPO}/${name}:dev-latest"
            else
              echo "Skipping $name. Dockerfile not found: $dockerfile"
            fi
          }

          build_if_exists "aia-web" "apps/web/Dockerfile" "."
          build_if_exists "aia-api" "apps/api/Dockerfile" "."
          build_if_exists "aia-orchestrator-worker" "services/orchestrator/Dockerfile" "."
          build_if_exists "aia-rag-worker" "services/rag/Dockerfile" "."
          build_if_exists "aia-search-worker" "services/search/Dockerfile" "."
YAML

# ==========================================================
# 3. GitHub Actions deploy workflow
# ==========================================================

cat > "${PROJECT_ROOT}/.github/workflows/aia-dev-deploy-k8s.yml" <<YAML
name: AIA Dev Deploy to Kubernetes

on:
  workflow_dispatch:
    inputs:
      apply_db:
        description: "Apply Supabase/Postgres dev schema"
        required: true
        default: "false"
        type: choice
        options:
          - "false"
          - "true"
      apply_k8s:
        description: "Apply Kubernetes dev manifests"
        required: true
        default: "true"
        type: choice
        options:
          - "true"
          - "false"

permissions:
  contents: read

env:
  DEV_NS: ${DEV_NS}
  STORAGE_NS: ${STORAGE_NS}
  MONITORING_NS: ${MONITORING_NS}
  SECURITY_NS: ${SECURITY_NS}
  DEV_DOMAIN: ${DEV_DOMAIN}
  PROD_DOMAIN: ${PROD_DOMAIN}

jobs:
  deploy:
    name: Deploy AIA Dev
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Install kubectl
        if: \${{ github.event.inputs.apply_k8s == 'true' }}
        uses: azure/setup-kubectl@v4
        with:
          version: latest

      - name: Configure kubeconfig
        if: \${{ github.event.inputs.apply_k8s == 'true' }}
        run: |
          set -euo pipefail
          if [ -z "\${{ secrets.KUBE_CONFIG_B64 }}" ]; then
            echo "Missing GitHub secret KUBE_CONFIG_B64"
            exit 1
          fi
          mkdir -p ~/.kube
          echo "\${{ secrets.KUBE_CONFIG_B64 }}" | base64 -d > ~/.kube/config
          chmod 600 ~/.kube/config
          kubectl config current-context
          kubectl get nodes -o wide

      - name: Safety check manifests
        run: |
          set -euo pipefail

          echo "Checking no production namespace is used..."
          if grep -R "ordinoxai-prod\\|aia-prod\\|iterlaw-prod" generated/k8s 2>/dev/null; then
            echo "Production namespace found. Refusing."
            exit 1
          fi

          echo "Checking root production domain is not used as ingress host..."
          if grep -R "host: ${PROD_DOMAIN}" generated/k8s 2>/dev/null; then
            echo "Root production domain found as ingress host. Refusing."
            exit 1
          fi

          echo "Checking no delete operation exists..."
          if grep -R "kubectl delete\\|cloudflare.com/client/v4\\|CF_API_TOKEN" . --exclude-dir=.git; then
            echo "Risky operation found. Refusing."
            exit 1
          fi

          echo "Safety check passed"

      - name: Apply DB schema
        if: \${{ github.event.inputs.apply_db == 'true' }}
        run: |
          set -euo pipefail
          if [ -z "\${{ secrets.SUPABASE_DB_URL_DEV }}" ]; then
            echo "Missing GitHub secret SUPABASE_DB_URL_DEV"
            exit 1
          fi

          sudo apt-get update
          sudo apt-get install -y postgresql-client

          psql "\${{ secrets.SUPABASE_DB_URL_DEV }}" -f generated/supabase/aia_dev_schema.sql

      - name: Apply Kubernetes manifests
        if: \${{ github.event.inputs.apply_k8s == 'true' }}
        run: |
          set -euo pipefail

          kubectl apply -f generated/k8s/00-namespaces/namespaces.yaml
          kubectl apply -f generated/k8s/10-storage/minio-dev.yaml
          kubectl apply -f generated/k8s/20-llm/ollama-dev-cpu.yaml
          kubectl apply -f generated/k8s/30-workers/aia-dev-workers.yaml
          kubectl apply -f generated/k8s/40-backup/supabase-dev-backup-cronjob.yaml
          kubectl apply -f generated/k8s/50-monitoring/aia-dev-monitoring-config.yaml
          kubectl apply -f generated/k8s/60-security/network-policies-dev.yaml
          kubectl apply -f generated/k8s/60-security/aia-dev-security-baseline.yaml
          kubectl apply -f generated/k8s/70-ingress/aia-dev-placeholder-web.yaml
          kubectl apply -f generated/k8s/70-ingress/aia-dev-ingress.yaml

      - name: Verify deployment
        if: \${{ github.event.inputs.apply_k8s == 'true' }}
        run: |
          set -euo pipefail

          kubectl -n "$DEV_NS" rollout status deploy/aia-dev-web --timeout=180s
          kubectl -n "$DEV_NS" rollout status deploy/aia-ollama-dev-cpu --timeout=240s || true
          kubectl -n "$DEV_NS" rollout status deploy/aia-orchestrator-dev-worker --timeout=180s
          kubectl -n "$DEV_NS" rollout status deploy/aia-rag-dev-worker --timeout=180s
          kubectl -n "$STORAGE_NS" rollout status deploy/minio-dev --timeout=240s || true

          kubectl -n "$DEV_NS" get pods -o wide
          kubectl -n "$STORAGE_NS" get pods -o wide
          kubectl -n "$DEV_NS" get svc
          kubectl -n "$DEV_NS" get ingress -o wide
YAML

# ==========================================================
# 4. Local Git push script
# ==========================================================

cat > "${PROJECT_ROOT}/scripts/git-push-aia-dev.sh" <<'BASH'
#!/usr/bin/env bash
set -euo pipefail

BRANCH="${BRANCH:-dev}"
COMMIT_MESSAGE="${COMMIT_MESSAGE:-chore: add AIA dev infrastructure automation}"

echo "=================================================="
echo "AIA local Git push helper"
echo "Branch: ${BRANCH}"
echo "Message: ${COMMIT_MESSAGE}"
echo "=================================================="

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "ERROR: this directory is not a Git repository."
  echo "Run from your repo root or initialise/connect the repo first."
  exit 1
fi

echo "Current remotes:"
git remote -v || true

if ! git remote get-url origin >/dev/null 2>&1; then
  echo "ERROR: no git remote named origin."
  echo "Add it first, example:"
  echo "  git remote add origin https://github.com/serverax/<repo-name>.git"
  exit 1
fi

git status -sb

git checkout -B "${BRANCH}"

git add \
  .github/workflows/aia-dev-ci.yml \
  .github/workflows/aia-dev-build-images.yml \
  .github/workflows/aia-dev-deploy-k8s.yml \
  scripts/aia-dev-full-infra-auto.sh \
  scripts/aia-dev-cicd-docs-auto.sh \
  scripts/git-push-aia-dev.sh \
  scripts/verify-aia-dev-infra.sh \
  docs/aia \
  generated/supabase \
  generated/k8s \
  generated/dns \
  generated/docs || true

if git diff --cached --quiet; then
  echo "No changes staged."
else
  git commit -m "${COMMIT_MESSAGE}"
fi

git push -u origin "${BRANCH}"

echo "Pushed to origin/${BRANCH}"
BASH

chmod +x "${PROJECT_ROOT}/scripts/git-push-aia-dev.sh"

# ==========================================================
# 5. Verification script
# ==========================================================

cat > "${PROJECT_ROOT}/scripts/verify-aia-dev-infra.sh" <<BASH
#!/usr/bin/env bash
set -euo pipefail

DEV_NS="${DEV_NS:-${DEV_NS}}"
STORAGE_NS="${STORAGE_NS:-${STORAGE_NS}}"
MONITORING_NS="${MONITORING_NS:-${MONITORING_NS}}"
SECURITY_NS="${SECURITY_NS:-${SECURITY_NS}}"
DEV_DOMAIN="${DEV_DOMAIN:-${DEV_DOMAIN}}"

REPORT_DIR="${REPORT_DIR:-/mnt/f/aia-dev/generated/evidence}"
mkdir -p "\${REPORT_DIR}"

REPORT="\${REPORT_DIR}/aia-dev-infra-verification-\$(date +%Y%m%d-%H%M%S).txt"

{
  echo "AIA DEV INFRA VERIFICATION"
  echo "Generated: \$(date -Is)"
  echo "Dev namespace: \${DEV_NS}"
  echo "Storage namespace: \${STORAGE_NS}"
  echo "Dev domain: \${DEV_DOMAIN}"
  echo ""

  echo "=== kubectl context ==="
  kubectl config current-context || true
  echo ""

  echo "=== namespaces ==="
  kubectl get ns "\${DEV_NS}" "\${STORAGE_NS}" "\${MONITORING_NS}" "\${SECURITY_NS}" -o wide || true
  echo ""

  echo "=== dev pods ==="
  kubectl -n "\${DEV_NS}" get pods -o wide || true
  echo ""

  echo "=== storage pods ==="
  kubectl -n "\${STORAGE_NS}" get pods -o wide || true
  echo ""

  echo "=== services ==="
  kubectl -n "\${DEV_NS}" get svc -o wide || true
  kubectl -n "\${STORAGE_NS}" get svc -o wide || true
  echo ""

  echo "=== ingress ==="
  kubectl -n "\${DEV_NS}" get ingress -o wide || true
  echo ""

  echo "=== rollout ==="
  kubectl -n "\${DEV_NS}" rollout status deploy/aia-dev-web --timeout=60s || true
  kubectl -n "\${DEV_NS}" rollout status deploy/aia-ollama-dev-cpu --timeout=60s || true
  kubectl -n "\${DEV_NS}" rollout status deploy/aia-orchestrator-dev-worker --timeout=60s || true
  kubectl -n "\${DEV_NS}" rollout status deploy/aia-rag-dev-worker --timeout=60s || true
  kubectl -n "\${STORAGE_NS}" rollout status deploy/minio-dev --timeout=60s || true
  echo ""

  echo "=== DNS ==="
  if command -v dig >/dev/null 2>&1; then
    dig +short "\${DEV_DOMAIN}" || true
  else
    echo "dig not installed"
  fi
  echo ""

  echo "=== HTTP check ==="
  if command -v curl >/dev/null 2>&1; then
    curl -Ik "https://\${DEV_DOMAIN}" || true
  else
    echo "curl not installed"
  fi
  echo ""

  echo "=== DB file check ==="
  ls -la /mnt/f/aia-dev/generated/supabase/aia_dev_schema.sql || true
  echo ""

  echo "NOTE:"
  echo "This confirms generated files and Kubernetes runtime state."
  echo "DB is only confirmed after psql migration output is provided."
} | tee "\${REPORT}"

echo ""
echo "Verification report saved:"
echo "\${REPORT}"
BASH

chmod +x "${PROJECT_ROOT}/scripts/verify-aia-dev-infra.sh"

# ==========================================================
# 6. Documentation guide
# ==========================================================

cat > "${PROJECT_ROOT}/docs/aia/AIA_DEV_INFRASTRUCTURE_GUIDE.md" <<DOC
# AIA Hiring Webapp DEV Infrastructure Guide

## 1. Purpose

This document describes the DEV infrastructure for the AIA Hiring Webapp under:

- Protected production domain: \`${PROD_DOMAIN}\`
- DEV test domain: \`${DEV_DOMAIN}\`
- DEV namespace: \`${DEV_NS}\`

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
- Modify root \`${PROD_DOMAIN}\`
- Modify Cloudflare DNS automatically
- Use production namespaces
- Commit real secrets to Git
- Deploy to production without a separate production pipeline

Only this dev host should be used:

\`${DEV_DOMAIN}\`

## 3. Namespaces

| Namespace | Purpose |
|---|---|
| \`${DEV_NS}\` | Main AIA dev workloads |
| \`${STORAGE_NS}\` | MinIO S3-compatible object storage |
| \`${MONITORING_NS}\` | Monitoring configuration baseline |
| \`${SECURITY_NS}\` | Security baseline configuration |

## 4. Supabase / Postgres Database

The schema file is:

\`generated/supabase/aia_dev_schema.sql\`

It creates three schemas:

| Schema | Purpose |
|---|---|
| \`orchestrator_dev\` | Jobs, job status, AI agent configuration, agent status |
| \`rag_dev\` | RAG documents, embeddings, queries, results |
| \`semantic_dev\` | Semantic indexes, documents, embeddings |

Required extensions:

- \`pgcrypto\`
- \`vector\`

### Orchestrator Tables

- \`orchestrator_dev.jobs\`
- \`orchestrator_dev.job_status\`
- \`orchestrator_dev.agent_config\`
- \`orchestrator_dev.agent_status\`

### RAG Tables

- \`rag_dev.documents\`
- \`rag_dev.embeddings\`
- \`rag_dev.queries\`
- \`rag_dev.results\`

### Semantic Search Tables

- \`semantic_dev.indexes\`
- \`semantic_dev.documents\`
- \`semantic_dev.embeddings\`

## 5. Storage

DEV storage uses MinIO:

- Deployment: \`minio-dev\`
- Namespace: \`${STORAGE_NS}\`
- Service: \`minio-dev.${STORAGE_NS}.svc.cluster.local:9000\`
- PVC: \`minio-dev-data\`
- Size: \`25Gi\`

Storage is intended for:

- CV uploads
- job description files
- extracted text artifacts
- generated reports
- temporary model artifacts
- backup exports

## 6. LLM Hosting Without GPU

DEV uses CPU-only Ollama:

- Deployment: \`aia-ollama-dev-cpu\`
- Namespace: \`${DEV_NS}\`
- Service: \`aia-ollama-dev-cpu.${DEV_NS}.svc.cluster.local:11434\`
- PVC: \`ollama-dev-models\`
- Size: \`40Gi\`

Recommended initial CPU models:

- \`llama3.2:3b\`
- \`qwen2.5:3b\`
- \`phi3.5\`

Do not start with large models on CPU. They will be slow.

## 7. Workers

Initial placeholder workers:

- \`aia-orchestrator-dev-worker\`
- \`aia-rag-dev-worker\`

These should later be replaced with real application images.

Expected future images:

- \`ghcr.io/serverax/<repo>/aia-orchestrator-worker:dev-latest\`
- \`ghcr.io/serverax/<repo>/aia-rag-worker:dev-latest\`
- \`ghcr.io/serverax/<repo>/aia-search-worker:dev-latest\`

## 8. Ingress

Ingress file:

\`generated/k8s/70-ingress/aia-dev-ingress.yaml\`

Target host:

\`${DEV_DOMAIN}\`

Ingress class:

\`traefik\`

TLS issuer expected:

\`letsencrypt-prod\`

## 9. DNS

DNS is manual only.

Do not change root \`${PROD_DOMAIN}\`.

Only add:

| Type | Name | Value |
|---|---|---|
| A | dev | Ingress public IP |

Start with Cloudflare proxy disabled.

Then test:

\`\`\`bash
dig +short ${DEV_DOMAIN}
curl -I https://${DEV_DOMAIN}
\`\`\`

## 10. CI/CD

Created workflows:

| Workflow | Purpose |
|---|---|
| \`.github/workflows/aia-dev-ci.yml\` | Validate scripts, manifests, and app build/tests |
| \`.github/workflows/aia-dev-build-images.yml\` | Build Docker images if Dockerfiles exist |
| \`.github/workflows/aia-dev-deploy-k8s.yml\` | Manual deployment to dev Kubernetes namespace |

## 11. GitHub Secrets Required

For deployment workflow:

| Secret | Purpose |
|---|---|
| \`KUBE_CONFIG_B64\` | Base64 kubeconfig for dev cluster deployment |
| \`SUPABASE_DB_URL_DEV\` | Optional DB URL for applying dev schema |

Create \`KUBE_CONFIG_B64\` locally:

\`\`\`bash
base64 -w0 ~/.kube/config
\`\`\`

Add it to GitHub:

\`Settings > Secrets and variables > Actions > New repository secret\`

## 12. Local Commands

Generate infra:

\`\`\`bash
bash /mnt/f/aia-dev/scripts/aia-dev-full-infra-auto.sh
\`\`\`

Apply infra:

\`\`\`bash
APPLY_K8S=true bash /mnt/f/aia-dev/scripts/aia-dev-full-infra-auto.sh
\`\`\`

Apply DB:

\`\`\`bash
psql "\$DATABASE_URL" -f /mnt/f/aia-dev/generated/supabase/aia_dev_schema.sql
\`\`\`

Push to GitHub:

\`\`\`bash
cd /mnt/f/aia-dev
BRANCH=dev COMMIT_MESSAGE="chore: add AIA dev infra" bash scripts/git-push-aia-dev.sh
\`\`\`

Verify:

\`\`\`bash
bash /mnt/f/aia-dev/scripts/verify-aia-dev-infra.sh
\`\`\`

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
DOC

# ==========================================================
# 7. DevOps handover
# ==========================================================

cat > "${PROJECT_ROOT}/docs/aia/DEVOPS_HANDOVER.md" <<DOC
# DevOps Handover - AIA Hiring Webapp DEV

## Objective

Deploy and operate the AIA Hiring Webapp DEV infrastructure under:

- Domain: \`${DEV_DOMAIN}\`
- Namespace: \`${DEV_NS}\`
- Storage namespace: \`${STORAGE_NS}\`

## What DevOps Receives

Directories:

- \`generated/k8s/\`
- \`generated/supabase/\`
- \`generated/dns/\`
- \`.github/workflows/\`
- \`scripts/\`
- \`docs/aia/\`

## Required Actions

### 1. Review Generated Manifests

\`\`\`bash
find /mnt/f/aia-dev/generated/k8s -type f | sort
\`\`\`

### 2. Apply Kubernetes Dev Infra

\`\`\`bash
cd /mnt/f/aia-dev
APPLY_K8S=true bash scripts/aia-dev-full-infra-auto.sh
\`\`\`

### 3. Apply Supabase/Postgres Schema

\`\`\`bash
psql "\$DATABASE_URL" -f generated/supabase/aia_dev_schema.sql
\`\`\`

### 4. Verify Runtime

\`\`\`bash
bash scripts/verify-aia-dev-infra.sh
\`\`\`

### 5. Configure DNS Manually

Add only:

- Type: A
- Name: dev
- Value: ingress public IP

Do not modify:

- root \`${PROD_DOMAIN}\`
- www
- api
- mail
- MX
- TXT
- SPF
- DKIM
- DMARC

### 6. Configure GitHub Secrets

Required:

- \`KUBE_CONFIG_B64\`
- \`SUPABASE_DB_URL_DEV\` if DB migration from GitHub is required

### 7. Validate GitHub Workflow

Run manually:

- AIA Dev CI
- AIA Dev Build Images
- AIA Dev Deploy to Kubernetes

## Non-Destructive Rules

The DevOps engineer must not:

- Run \`kubectl delete\`
- Replace production ingress
- Reuse production namespace
- Change root DNS
- Commit secrets
- Expose MinIO console publicly without authentication and network controls

## Evidence Required

Return these outputs:

\`\`\`bash
kubectl get ns | grep aia-dev
kubectl -n aia-dev get pods -o wide
kubectl -n aia-dev-storage get pods -o wide
kubectl -n aia-dev get ingress -o wide
kubectl -n aia-dev get svc
curl -I https://${DEV_DOMAIN}
\`\`\`

Also provide DB migration output from:

\`\`\`bash
psql "\$DATABASE_URL" -f generated/supabase/aia_dev_schema.sql
\`\`\`
DOC

# ==========================================================
# 8. Developer handover
# ==========================================================

cat > "${PROJECT_ROOT}/docs/aia/DEVELOPER_HANDOVER.md" <<DOC
# Developer Handover - AIA Hiring Webapp

## Environment

DEV base domain:

\`${DEV_DOMAIN}\`

Main namespace:

\`${DEV_NS}\`

Internal LLM endpoint:

\`http://aia-ollama-dev-cpu.${DEV_NS}.svc.cluster.local:11434\`

Internal object storage endpoint:

\`http://minio-dev.${STORAGE_NS}.svc.cluster.local:9000\`

## Database Schemas

Use these schemas in DEV:

- \`orchestrator_dev\`
- \`rag_dev\`
- \`semantic_dev\`

## Orchestrator Service

Use:

- \`orchestrator_dev.jobs\`
- \`orchestrator_dev.job_status\`
- \`orchestrator_dev.agent_config\`
- \`orchestrator_dev.agent_status\`

Expected workflow:

1. API creates job in \`orchestrator_dev.jobs\`
2. Worker locks job
3. Worker updates \`job_status\`
4. Worker calls RAG/search/LLM
5. Worker stores final result in job status metadata or application tables

## RAG Service

Use:

- \`rag_dev.documents\`
- \`rag_dev.embeddings\`
- \`rag_dev.queries\`
- \`rag_dev.results\`

Expected workflow:

1. Upload CV/job document to storage
2. Extract text
3. Chunk content
4. Store chunks in \`rag_dev.documents\`
5. Generate embeddings
6. Store vectors in \`rag_dev.embeddings\`
7. Query and store retrieval audit in \`rag_dev.queries\` and \`rag_dev.results\`

## Semantic Search Service

Use:

- \`semantic_dev.indexes\`
- \`semantic_dev.documents\`
- \`semantic_dev.embeddings\`

Initial indexes:

- \`candidate-cv-dev-index\`
- \`job-description-dev-index\`
- \`interview-qa-dev-index\`

## Required Application Services

The developer should create or connect:

| Service | Expected path |
|---|---|
| Web frontend | \`apps/web\` |
| API backend | \`apps/api\` |
| Orchestrator worker | \`services/orchestrator\` |
| RAG worker | \`services/rag\` |
| Search worker | \`services/search\` |

Each deployable service should include a Dockerfile.

The GitHub build pipeline detects:

- \`apps/web/Dockerfile\`
- \`apps/api/Dockerfile\`
- \`services/orchestrator/Dockerfile\`
- \`services/rag/Dockerfile\`
- \`services/search/Dockerfile\`

## Required API Endpoints

Minimum API endpoints:

| Endpoint | Purpose |
|---|---|
| \`GET /health\` | Basic process health |
| \`GET /ready\` | DB/storage/LLM readiness |
| \`POST /jobs\` | Create orchestrator job |
| \`GET /jobs/:id\` | Read job status |
| \`POST /documents/upload\` | Upload CV/job file |
| \`POST /rag/query\` | Query RAG |
| \`POST /match/candidate-job\` | Candidate/job matching |

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

\`\`\`bash
kubectl -n aia-dev exec deploy/aia-ollama-dev-cpu -- ollama pull llama3.2:3b
\`\`\`

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
- Deployment passes in \`${DEV_NS}\`
DOC

# ==========================================================
# 9. Evidence report template
# ==========================================================

cat > "${OUT_DIR}/evidence/AIA_DEV_INFRA_STATUS_TEMPLATE.md" <<DOC
# AIA DEV Infrastructure Status

## Generated Files

Run:

\`\`\`bash
find /mnt/f/aia-dev/generated -type f | sort
\`\`\`

Paste output here.

## Kubernetes Evidence

Run:

\`\`\`bash
kubectl get ns | grep aia-dev
kubectl -n aia-dev get pods -o wide
kubectl -n aia-dev-storage get pods -o wide
kubectl -n aia-dev get svc
kubectl -n aia-dev get ingress -o wide
\`\`\`

Paste output here.

## Database Evidence

Run:

\`\`\`bash
psql "\$DATABASE_URL" -f /mnt/f/aia-dev/generated/supabase/aia_dev_schema.sql
\`\`\`

Then verify:

\`\`\`sql
select schema_name
from information_schema.schemata
where schema_name in ('orchestrator_dev', 'rag_dev', 'semantic_dev');

select table_schema, table_name
from information_schema.tables
where table_schema in ('orchestrator_dev', 'rag_dev', 'semantic_dev')
order by table_schema, table_name;
\`\`\`

Paste output here.

## DNS Evidence

Run:

\`\`\`bash
dig +short dev.ordinoxai.com
curl -I https://dev.ordinoxai.com
\`\`\`

Paste output here.

## Final Status

| Area | Status |
|---|---|
| K8s namespaces | Pending evidence |
| Storage | Pending evidence |
| LLM | Pending evidence |
| Workers | Pending evidence |
| Ingress | Pending evidence |
| DB schemas | Pending evidence |
| CI/CD | Pending evidence |
| DNS | Manual / pending evidence |
DOC

# ==========================================================
# 10. Safety scan
# ==========================================================

echo ""
echo "Generated CI/CD and documentation files:"
find "${PROJECT_ROOT}/.github/workflows" "${PROJECT_ROOT}/scripts" "${PROJECT_ROOT}/docs/aia" "${OUT_DIR}/evidence" -type f | sort

echo ""
echo "Safety scan:"
if grep -R "kubectl delete\|curl.*api.cloudflare\|CF_API_TOKEN\|cloudflare.com/client/v4" \
  "${PROJECT_ROOT}/.github" \
  "${PROJECT_ROOT}/scripts" \
  "${PROJECT_ROOT}/docs/aia" \
  --exclude="aia-dev-cicd-docs-auto.sh" 2>/dev/null; then
  echo "WARNING: risky command text found. Review above."
else
  echo "PASS: no kubectl delete or Cloudflare API mutation found."
fi

echo ""
echo "Root domain check:"
if grep -R "host: ${PROD_DOMAIN}" "${PROJECT_ROOT}/.github" "${PROJECT_ROOT}/docs/aia" "${OUT_DIR}" 2>/dev/null; then
  echo "WARNING: root production domain used as host somewhere. Review."
else
  echo "PASS: root production domain is not used as ingress host."
fi

# ==========================================================
# 11. Optional Git push
# ==========================================================

if [[ "${RUN_GIT_PUSH}" == "true" ]]; then
  cd "${PROJECT_ROOT}"
  BRANCH=dev COMMIT_MESSAGE="${GIT_COMMIT_MESSAGE}" bash scripts/git-push-aia-dev.sh
else
  echo ""
  echo "Git push not executed."
  echo "To push:"
  echo "  cd ${PROJECT_ROOT}"
  echo "  BRANCH=dev COMMIT_MESSAGE=\"${GIT_COMMIT_MESSAGE}\" bash scripts/git-push-aia-dev.sh"
fi

echo ""
echo "Done."
echo ""
echo "Created:"
echo "- GitHub CI/CD workflows"
echo "- Local Git push script"
echo "- Kubernetes verification script"
echo "- Infrastructure guide"
echo "- DevOps handover"
echo "- Developer handover"
echo "- Evidence template"
