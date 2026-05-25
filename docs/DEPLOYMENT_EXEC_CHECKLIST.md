# AIA Deployment Execution Checklist

Project-accurate, copy/paste-ready run checklist for deployment teams.

## 0) Set context and fail-fast shell

```bash
set -euo pipefail
cd /path/to/aia
git checkout main
git pull --ff-only
```

Expected:
- On latest `main`
- No merge conflicts

---

## 1) Normalize LF endings (critical blocker fix)

Use whichever tool is available.

### Option A: `dos2unix`

```bash
dos2unix scripts/security/pre_deploy_check.sh verify-deployment-manifests.sh
```

### Option B: `sed` fallback (if `dos2unix` unavailable)

```bash
sed -i 's/\r$//' scripts/security/pre_deploy_check.sh verify-deployment-manifests.sh
```

Validate:

```bash
bash -n scripts/security/pre_deploy_check.sh
bash -n verify-deployment-manifests.sh
```

Expected:
- No syntax output/errors from `bash -n`

---

## 2) Confirm kube context for staging

```bash
kubectl config current-context
kubectl get nodes -o wide
```

Expected:
- Intended staging/pre-prod context
- Nodes `Ready`

---

## 3) Run pre-deploy gate

```bash
bash scripts/security/pre_deploy_check.sh
```

Expected:
- Final verdict line shows `GO` (or explicit non-blocking warnings only)

If needed (live mode):

```bash
bash scripts/security/pre_deploy_check.sh --live
```

---

## 4) Run manifest validation

```bash
bash verify-deployment-manifests.sh
```

Expected:
- No CRLF parse errors
- No manifest validation errors (or clearly documented CRD-dependent warnings only)

---

## 5) Execute staging smoke flow

Use the canonical runbook steps from:

- `docs/STAGING-DEPLOY-RUNBOOK.md` (kubectl flow), or
- `docs/STAGING-DEPLOY-RUNBOOK-FLUX.md` (Flux flow)

Minimum smoke checks:

```bash
kubectl -n ordinox-ai get deploy,svc,pods
kubectl -n ordinox-ai get endpoints -o wide
kubectl -n ordinox-ai get events --sort-by='.lastTimestamp' | tail -20
```

Expected:
- Workloads healthy
- Endpoints populated
- No critical warning events

---

## 6) Capture evidence artifacts

Create a timestamped evidence directory and save outputs:

```bash
TS=$(date +%Y%m%d-%H%M%S)
EVIDENCE_DIR="reports/deployment-evidence/$TS"
mkdir -p "$EVIDENCE_DIR"

kubectl config current-context > "$EVIDENCE_DIR/context.txt"
kubectl get nodes -o wide > "$EVIDENCE_DIR/nodes.txt"
kubectl -n ordinox-ai get deploy,svc,pods -o wide > "$EVIDENCE_DIR/workloads.txt"
kubectl -n ordinox-ai get endpoints -o wide > "$EVIDENCE_DIR/endpoints.txt"
kubectl -n ordinox-ai get events --sort-by='.lastTimestamp' > "$EVIDENCE_DIR/events.txt"
```

Expected:
- Evidence files present under `reports/deployment-evidence/<timestamp>/`

---

## 7) Complete release signoff

Fill and finalize:
- `docs/RELEASE_SIGNOFF_2026-05-25.md`

Cross-reference evidence from:
- `docs/DEPLOYMENT_READINESS_PASS_2026-05-25.md`
- `docs/ROLLBACK_CHECKLIST.md`
- `docs/POST_DEPLOYMENT_MONITORING_PLAN_2026-05-25.md`

Expected:
- Signed/approved release record (per stakeholder process)

---

## 8) Confirm checklist completion to stakeholders

Send handover status with:
- Gate results
- Smoke test result
- Evidence location
- Signoff status
- Go/No-Go decision

Use:
- `docs/DEPLOYMENT_HANDOVER_BRIEF_2026-05-25.md`

---

## 9) Publish deployment window and execute rollout

- Share timeline + support coverage
- Execute rollout per:
  - `docs/01-PRODUCTION-DEPLOYMENT-GUIDE.md`
  - `docs/02-OPERATIONS-RUNBOOK.md`

During rollout, keep rollback ready:

```bash
bash scripts/compliance/rollback-blue-green.sh
# or
bash scripts/rollback-to-blue.sh
```

---

## Go/No-Go Gate (must all be true)

- [ ] LF normalization complete, no shell parse errors
- [ ] `pre_deploy_check.sh` passes in staging
- [ ] Manifest verification completes cleanly
- [ ] Staging smoke flow passes
- [ ] Evidence captured and linked
- [ ] Release signoff approved
- [ ] Deployment timeline communicated
