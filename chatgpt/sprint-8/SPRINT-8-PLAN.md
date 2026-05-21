# Sprint 8 Production Hardening Plan

## Scope

Sprint 8 runs in Week 16 after Sprint 7 is accepted on the real cluster.

Required deliverables:

- Load testing for 1,000+ concurrent users
- Security penetration testing
- Disaster recovery procedures
- Blue-green deployment validation
- SLA definition and production readiness checklist

## Cluster Preconditions

Do not execute Sprint 8 before these are true:

- K3s cluster is operational
- Echo, Orchestrator, Analyst, Frontend, Editor, WASM security, and Compliance Service are deployed
- PostgreSQL, Redis, Qdrant, Milvus, and observability stack are running
- Production network policies and ingress are active
- Sprint 7 compliance smoke validation passed

## Acceptance Evidence

Sprint 8 is complete only when these artifacts are captured from the real system:

- Load test report for 1,000+ concurrent users
- Security scan report with no critical or high findings accepted without human sign-off
- Disaster recovery drill result with RTO/RPO measured
- Blue-green deployment validation result and rollback proof
- Signed production readiness checklist

## Prepared Assets

- `scripts/testing/load_locustfile.py`
- `scripts/testing/run_load_test.ps1`
- `scripts/testing/run_zap_baseline.ps1`
- `scripts/testing/dr_restore_check.ps1`
- `scripts/testing/blue_green_validate.ps1`
- `chatgpt/sprint-8/DISASTER-RECOVERY-RUNBOOK.md`
- `chatgpt/sprint-8/PRODUCTION-READINESS-CHECKLIST.md`
- `chatgpt/sprint-8/SLA.md`
