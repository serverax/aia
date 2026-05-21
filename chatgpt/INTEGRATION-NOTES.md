# Sprint 7-8 Integration Points

## Sprint 7 Dependencies

- Requires Orchestrator Agent from Sprint 2.
- Requires PostgreSQL from Sprint 1 for audit storage.
- Requires Redis from Sprint 1 for agent messaging.
- Requires Compliance Service deployment from `infrastructure/compliance/compliance-service.yaml`.
- Requires production NetworkPolicies before real validation.

## Sprint 8 Dependencies

- Requires full system running in K3s.
- Requires Echo, Orchestrator, Analyst, Frontend, Editor, WASM security, and Compliance Service deployed.
- Requires PostgreSQL, Redis, Qdrant, Milvus, and observability stack operational.
- Requires Sprint 7 real-cluster validation completed.

## Week 14 Deployment Checklist

- [ ] Human confirms the cluster is not bare and contains Sprint 1-6 services.
- [ ] Human provides or confirms the manifest/resource list already running.
- [ ] K3s cluster running.
- [ ] Namespace `synthetic-enterprise` exists.
- [ ] PostgreSQL reachable.
- [ ] Redis reachable.
- [ ] Orchestrator deployed.
- [ ] Analyst deployed.
- [ ] Frontend deployed.
- [ ] Editor deployed.
- [ ] WASM security deployed.
- [ ] Compliance Service image available.
- [ ] Compliance manifests applied.
- [ ] NetworkPolicies active.
- [ ] `scripts/testing/sprint7_cluster_smoke.ps1` passes.

## Week 14 Pass/Fail Thresholds

Blockers:

- `kubectl` cannot reach the K3s cluster.
- Namespace `synthetic-enterprise` is missing.
- PostgreSQL or Redis service has no ready endpoints.
- Any Sprint 1-6 required deployment is missing or not ready within 120 seconds.
- Sprint 7 deployment fails to apply.
- Sprint 7 smoke validation fails.

Warnings:

- Compliance Service already exists before Sprint 7 deployment. Verify ownership before applying manifests.
- Compliance NetworkPolicy is not present before Sprint 7 deployment. It must be present after applying `infrastructure/compliance/`.

Rollback:

- Use `scripts/deployment/sprint7_rollback.ps1` if deployment succeeds but smoke validation fails, audit validation fails, or a NetworkPolicy blocks a critical dependency.
- Rollback deletes the Sprint 7 compliance manifests and verifies the Compliance Service deployment, service, and NetworkPolicy are removed.

## Week 16 Execution Checklist

- [ ] Sprint 7 approved on real cluster.
- [ ] Load test target URL confirmed.
- [ ] OWASP ZAP target URL confirmed.
- [ ] Backup and restore credentials available.
- [ ] Blue-green deployment labels and rollout process confirmed.
- [ ] Load tests run successfully.
- [ ] Security baseline clear or exceptions approved by human.
- [ ] Disaster recovery procedures validated.
- [ ] Blue-green deployment and rollback verified.
