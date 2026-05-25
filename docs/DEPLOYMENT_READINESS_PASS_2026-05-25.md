# Deployment Readiness Pass (2026-05-25)

## Objective

Validate deployment readiness after PR #6 merge, capture smoke-test evidence, and prepare rollback/handover artifacts for the deployment team.

## Environment and Scope

- Repository: `main` branch at `F:/aia`
- Validation context: active kube context `aks-iterlaw-we-prod`
- Scope: deployment scripts, manifests, runbooks, readiness gates, and namespace consistency

## Checks Executed

1. **Pre-deploy gate script execution**
   - Command: `bash scripts/security/pre_deploy_check.sh`
   - Result: **FAILED (script execution error)**
   - Finding: CRLF line endings in shell script cause `bash` parse failures on this runner (`$'\r'` errors).

2. **Manifest verification script**
   - Command: `bash verify-deployment-manifests.sh`
   - Result: **PARTIAL / UNRELIABLE**
   - Findings:
     - Script also has CRLF parsing noise.
     - Validation path attempts to reach `148.251.247.56:6443` and times out.
     - Script prints a success footer even with upstream dry-run failures; treat as non-authoritative.

3. **Cluster context and namespace smoke inventory**
   - Commands:
     - `kubectl config current-context`
     - `kubectl get nodes -o wide`
     - `kubectl get ns ordinox-ai synthetic-enterprise`
     - `kubectl get deployments -n ordinox-ai`
     - `kubectl -n synthetic-enterprise get deploy,svc,pods`
   - Results:
     - Context reachable (`aks-iterlaw-we-prod`), node is `Ready`.
     - Namespace state is inconsistent with project expectations (`synthetic-enterprise` exists; `ordinox-ai` missing in namespace query output).
     - No application resources found in either deployment namespace during this pass.

4. **Static deployment consistency review**
   - `rg` scans across `scripts/`, `docs/`, and `infrastructure/` confirmed mixed namespace usage (`synthetic-enterprise` and `ordinox-ai`) and mixed ingress naming in blue-green documentation/scripts.

## Remediations Applied in This Pass

1. **Namespace defaults aligned to `ordinox-ai` in deployment scripts**
   - Updated:
     - `scripts/compliance/rollout-gate.sh`
     - `scripts/compliance/rollback-blue-green.sh`
     - `scripts/rollback-to-blue.sh`

2. **Blue-green ingress target aligned**
   - `scripts/compliance/rollback-blue-green.sh` now defaults to `compliance-service-green-canary` and targets `compliance-service-green` deployment rollback path.

3. **Operational docs corrected for namespace/ingress alignment**
   - Updated:
     - `docs/01-PRODUCTION-DEPLOYMENT-GUIDE.md`
     - `docs/02-OPERATIONS-RUNBOOK.md`

## Deployment Readiness Verdict

Status: **CONDITIONALLY READY (CONFIG REQUIRED)**

Ready:
- Codebase and CI gates are green from previous merge validation.
- Rollout/rollback scripts and core ops docs now align with current namespace target.

Not yet ready (must complete before production rollout):
- Normalize line endings of bash gate scripts used in deployment (`pre_deploy_check.sh`, `verify-deployment-manifests.sh`) for deterministic shell execution.
- Confirm authoritative target cluster and namespace convention (single source of truth).
- Run full pre-deploy gate and smoke flow in the deployment-owned staging/pre-prod environment.

## Required Next Actions (Deployment Team)

1. Run line-ending normalization on deployment shell scripts in Linux CI or enforce LF via repo policy.
2. Re-run:
   - `bash scripts/security/pre_deploy_check.sh`
   - `bash verify-deployment-manifests.sh`
3. Execute staging smoke tests from `docs/STAGING-DEPLOY-RUNBOOK*.md`.
4. Capture evidence files under `reports/` and attach to release ticket/signoff.
