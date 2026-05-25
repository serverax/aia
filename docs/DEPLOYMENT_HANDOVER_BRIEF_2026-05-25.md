# Deployment Handover Brief (2026-05-25)

## Purpose

Provide the deployment team with the minimum complete package to run deployment, validate health, and execute rollback safely.

## Handover Meeting Agenda (30 min)

1. Release scope and key fixes included in this drop.
2. Deployment readiness findings and open blockers.
3. Staging smoke test expectations and evidence capture.
4. Rollback triggers and command walkthrough.
5. Post-deployment monitoring and support protocol.

## Inputs to Share Before Meeting

- `docs/DEPLOYMENT_READINESS_PASS_2026-05-25.md`
- `docs/RELEASE_SIGNOFF_2026-05-25.md`
- `docs/ROLLBACK_CHECKLIST.md`
- `docs/STAGING-DEPLOY-RUNBOOK.md`
- `docs/STAGING-DEPLOY-RUNBOOK-FLUX.md`

## Access Checklist for Deployment Team

- GitHub repository access (`serverax/aia`)
- Cluster credentials (`KUBECONFIG`) for target environment
- Secret management path for deployment-time secrets
- Permission to run rollout and rollback scripts
- Access to monitoring stack (Prometheus/Grafana/log aggregation)

## Critical Notes for This Handover

- Deployment artifacts have mixed legacy references (`synthetic-enterprise`) and current target (`ordinox-ai`); this pass aligned key scripts and runbooks to `ordinox-ai`.
- Shell pre-deploy gates require LF-compatible script execution in deployment environment.
- Staging smoke evidence in this pass is limited by environment state; deployment team must execute authoritative smoke checks in target staging.

## Post-Deployment Monitoring Plan (First 2 Hours)

1. Verify pod, deployment, and endpoint health every 5 minutes.
2. Track latency/error budgets and canary split behavior.
3. Watch warning events and restart counts.
4. Hold promotion if any rollback trigger condition appears.

## Support Model

- Deployment lead: executes runbook/checklist and captures evidence.
- Engineering on-call: available for script/config/code fixes during initial window.
- Security/compliance reviewer: validates policy and audit behavior after deployment.

## Escalation Path

1. Deployment issue (operational): deployment lead -> platform owner.
2. Application regression: deployment lead -> engineering on-call.
3. Policy/admission failure: deployment lead -> security/compliance owner.

If unresolved after 15 minutes in any category, trigger rollback and log incident.
