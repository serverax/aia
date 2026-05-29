# `k8s/` — bootstrap placeholder, **not** a production deploy

This directory contains two manifests that establish the `ordinoxai-prod`
namespace and a tiny nginx-served HTML placeholder:

- **`namespace.yaml`** — `Namespace ordinoxai-prod` with PSS `baseline`
  labels (`enforce` / `audit` / `warn`).
- **`web.yaml`** — `ConfigMap` carrying a static "OrdinoxAI — bootstrap
  online" page; a `Deployment` running `nginxinc/nginx-unprivileged:1.27-alpine`
  (2 replicas, non-root, `allowPrivilegeEscalation: false`, capabilities
  dropped, `readinessProbe` + `livenessProbe` on `GET /:8080`); and a
  `ClusterIP` `Service` exposing port 80 → 8080.

## What this *is*

A minimal namespace plus a reachable "the cluster is up" page. Useful for:

- Confirming the cluster talks to the configured registry.
- Verifying PSS labels apply correctly.
- Smoke-testing Service / DNS plumbing before real workloads land.

## What this is **not**

This is **not** the production AIA application. Specifically, `k8s/`
**does not provide**:

- The Hiring API (`apps/api`) Deployment.
- The orchestrator, compliance, RAG, editor, or realtime-collab Deployments.
- An `Ingress`, `Gateway`, or any external exposure — only `ClusterIP`.
- Secret / `ConfigMap` wiring for `AIA_AUTH_SECRET_KEY`, `POSTGRES_*`,
  `ANTHROPIC_API_KEY`, etc.

The real deploy surface lives in `helm/synthetic-enterprise/` (Helm chart)
and is gated separately. Treat `k8s/` as bootstrap-only.

## CI validation

`.github/workflows/k8s-validate.yml` runs
`kubectl apply --dry-run=client -f k8s/` on every push and PR. That proves
the YAML parses and matches the expected Kubernetes schemas; it does **not**
prove anything is deployable end-to-end.

## How to apply (manually, against a non-prod cluster)

```sh
kubectl apply --dry-run=server -f k8s/namespace.yaml
kubectl apply --dry-run=server -f k8s/web.yaml
# Only after a server-side dry-run looks clean:
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/web.yaml
```

Do **not** apply against a production cluster without an explicit operator
review of probes, resource limits, image provenance, and PSS posture.
