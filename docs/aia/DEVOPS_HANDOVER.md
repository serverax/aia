# DevOps Handover - AIA Hiring Webapp DEV

## Objective

Deploy and operate the AIA Hiring Webapp DEV infrastructure under:

- Domain: `dev.ordinoxai.com`
- Namespace: `aia-dev`
- Storage namespace: `aia-dev-storage`

## What DevOps Receives

Directories:

- `generated/k8s/`
- `generated/supabase/`
- `generated/dns/`
- `.github/workflows/`
- `scripts/`
- `docs/aia/`

## Required Actions

### 1. Review Generated Manifests

```bash
find /mnt/f/aia-dev/generated/k8s -type f | sort
```

### 2. Apply Kubernetes Dev Infra

```bash
cd /mnt/f/aia-dev
APPLY_K8S=true bash scripts/aia-dev-full-infra-auto.sh
```

### 3. Apply Supabase/Postgres Schema

```bash
psql "$DATABASE_URL" -f generated/supabase/aia_dev_schema.sql
```

### 4. Verify Runtime

```bash
bash scripts/verify-aia-dev-infra.sh
```

### 5. Configure DNS Manually

Add only:

- Type: A
- Name: dev
- Value: ingress public IP

Do not modify:

- root `ordinoxai.com`
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

- `KUBE_CONFIG_B64`
- `SUPABASE_DB_URL_DEV` if DB migration from GitHub is required

### 7. Validate GitHub Workflow

Run manually:

- AIA Dev CI
- AIA Dev Build Images
- AIA Dev Deploy to Kubernetes

## Non-Destructive Rules

The DevOps engineer must not:

- Run `kubectl delete`
- Replace production ingress
- Reuse production namespace
- Change root DNS
- Commit secrets
- Expose MinIO console publicly without authentication and network controls

## Evidence Required

Return these outputs:

```bash
kubectl get ns | grep aia-dev
kubectl -n aia-dev get pods -o wide
kubectl -n aia-dev-storage get pods -o wide
kubectl -n aia-dev get ingress -o wide
kubectl -n aia-dev get svc
curl -I https://dev.ordinoxai.com
```

Also provide DB migration output from:

```bash
psql "$DATABASE_URL" -f generated/supabase/aia_dev_schema.sql
```
