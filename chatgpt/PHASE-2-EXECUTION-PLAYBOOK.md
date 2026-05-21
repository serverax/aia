# PHASE 2 EXECUTION PLAYBOOK

## Purpose

Phase 2 validates the production Talos deployment using the hardened Sprint 8 scripts. This playbook defines exact command sequences, evidence capture, validation gates, and failure handling. Do not run Phase 2 against AKS, local Docker, or stale kube contexts.

## Pre-execution checklist

- [ ] Ops has confirmed Talos credentials and provided kubeconfig.
- [ ] Matching `~/.talos/config` is available for Talos node diagnostics.
- [ ] Gemini backend is deployed and healthy on prod Talos, if included in this run.
- [ ] Cursor regression suite is ready locally.
- [ ] Claude Code local Talos triage report is available.
- [ ] `compliance-service` is deployed in `synthetic-enterprise`.
- [ ] `llm-api-keys` secret exists in `synthetic-enterprise`.
- [ ] Known placeholder/runtime limitations are documented.
- [ ] Run ID is chosen: `RUN_ID=phase2-$(date +%Y%m%d-%H%M%S)`.

## Evidence directory setup

Command:

```bash
export RUN_ID="phase2-$(date +%Y%m%d-%H%M%S)"
export PHASE2_DIR="/tmp/${RUN_ID}"
mkdir -p "${PHASE2_DIR}"
```

Validation gate:

```bash
test -d "${PHASE2_DIR}" || { echo "evidence directory missing"; exit 1; }
```

If this fails, stop and fix local filesystem permissions.

## Phase 2 Step 1: Verify Talos Access

Command:

```bash
export KUBECONFIG=<ops-provided-kubeconfig>
kubectl config current-context
kubectl get nodes -o wide
talosctl version
```

Expected output:

```text
kubectl config current-context
talos-prod or equivalent approved Talos context

kubectl get nodes -o wide
all expected nodes show Ready

talosctl version
Client and Server sections return without TLS/CA error
```

Evidence capture:

```bash
kubectl config current-context | tee "${PHASE2_DIR}/phase2-kube-context.txt"
kubectl config view --minify --raw > "${PHASE2_DIR}/phase2-kubeconfig-minify.yaml"
kubectl get nodes -o wide | tee "${PHASE2_DIR}/phase2-nodes.txt"
talosctl version 2>&1 | tee "${PHASE2_DIR}/phase2-talosctl-version.txt"
```

Validation gates:

- Context must match Ops-provided Talos context.
- Nodes must be `Ready`.
- `talosctl version` must not contain `certificate signed by unknown authority`.

If FAIL:

```bash
echo "STOP: invalid Talos credentials or wrong context"
```

Escalate to Ops with:

- `phase2-kube-context.txt`
- `phase2-nodes.txt`
- `phase2-talosctl-version.txt`

Do not continue to tests.

## Phase 2 Step 2: Verify application baseline

Command:

```bash
kubectl -n synthetic-enterprise get deploy,pods,svc,endpoints -o wide
kubectl -n synthetic-enterprise rollout status deployment/compliance-service --timeout=120s
```

Evidence capture:

```bash
kubectl -n synthetic-enterprise get deploy,pods,svc,endpoints -o wide \
  | tee "${PHASE2_DIR}/phase2-app-baseline.txt"
kubectl -n synthetic-enterprise get events --sort-by=.lastTimestamp \
  > "${PHASE2_DIR}/phase2-events-before.txt"
```

Validation gates:

- `compliance-service` deployment is fully available.
- Endpoints are populated.
- No pods in `CrashLoopBackOff`, `ImagePullBackOff`, or `Pending`.

If FAIL:

```bash
kubectl -n synthetic-enterprise describe deployment compliance-service \
  > "${PHASE2_DIR}/phase2-compliance-deploy-describe.txt"
kubectl -n synthetic-enterprise get events --sort-by=.lastTimestamp \
  > "${PHASE2_DIR}/phase2-baseline-failure-events.txt"
```

Escalate to platform owner.

## Phase 2 Step 3: Run Load Test Script

Command:

```powershell
C:\Program Files\PowerShell\7\pwsh.exe -File scripts/testing/run_load_test.ps1 `
  -HostUrl <target-url> `
  -Users 1000 `
  -SpawnRate 50 `
  -RunTime 30m `
  -Docker `
  -ReportPath scripts/testing/load-test-report.html `
  *> /tmp/phase2-load-test.log
```

If running from WSL:

```bash
pwsh -File scripts/testing/run_load_test.ps1 \
  -HostUrl <target-url> \
  -Users 1000 \
  -SpawnRate 50 \
  -RunTime 30m \
  -Docker \
  -ReportPath scripts/testing/load-test-report.html \
  *> "${PHASE2_DIR}/phase2-load-test.log"
```

Expected output:

- Locust summary appears in log.
- Report file is generated.
- No sustained failures.

Evidence capture:

```bash
cp scripts/testing/load-test-report.html "${PHASE2_DIR}/phase2-load-test-report.html"
grep -E "Aggregated|FAIL|Error|GET|POST|p95" "${PHASE2_DIR}/phase2-load-test.log" \
  > "${PHASE2_DIR}/phase2-load-test-summary.txt" || true
kubectl -n synthetic-enterprise get pods -o wide \
  > "${PHASE2_DIR}/phase2-pods-after-load.txt"
kubectl -n synthetic-enterprise get events --sort-by=.lastTimestamp \
  > "${PHASE2_DIR}/phase2-events-after-load.txt"
```

Validation gates:

- p95 latency for health/readiness `< 500 ms`.
- p95 latency for evaluation `< 1,500 ms`.
- Error rate `< 0.1%`.
- Test duration `< 60 min`.
- No pod restarts.

If FAIL:

```bash
kubectl -n synthetic-enterprise logs deployment/compliance-service --tail=500 \
  > "${PHASE2_DIR}/phase2-compliance-logs-after-load-fail.txt"
kubectl -n synthetic-enterprise describe pods \
  > "${PHASE2_DIR}/phase2-pod-describe-after-load-fail.txt"
```

Escalation:

- Gemini if backend/evaluate endpoint errors dominate.
- Ops if node pressure, network errors, or pod scheduling errors dominate.
- Program leadership if failure cannot be triaged within 30 minutes.

Stop rule: If error rate exceeds `10%` or p95 exceeds `5s`, stop Phase 2.

## Phase 2 Step 4: Run ZAP Security Baseline

Command:

```powershell
C:\Program Files\PowerShell\7\pwsh.exe -File scripts/testing/run_zap_baseline.ps1 `
  -TargetUrl <target-url> `
  -ReportPath scripts/testing/zap-baseline-report.html `
  *> /tmp/phase2-zap.log
```

WSL command:

```bash
pwsh -File scripts/testing/run_zap_baseline.ps1 \
  -TargetUrl <target-url> \
  -ReportPath scripts/testing/zap-baseline-report.html \
  *> "${PHASE2_DIR}/phase2-zap.log"
```

Expected output:

- ZAP baseline completes.
- `FAIL-NEW: 0`.
- Report file is generated.

Evidence capture:

```bash
cp scripts/testing/zap-baseline-report.html "${PHASE2_DIR}/phase2-zap-report.html"
grep -E "FAIL-NEW|WARN-NEW|PASS:|CRITICAL|HIGH|MEDIUM" "${PHASE2_DIR}/phase2-zap.log" \
  > "${PHASE2_DIR}/phase2-zap-risk-summary.txt" || true
```

Validation gates:

- Critical findings: `0`.
- High findings: `0` unless security owner approves exception.
- Medium findings: `<= 5` with documented disposition.
- Test duration `< 2h`.

If FAIL:

```bash
cp "${PHASE2_DIR}/phase2-zap.log" "${PHASE2_DIR}/phase2-zap-failure.log"
```

Escalate to security/Claude Code with:

- ZAP HTML report
- risk summary
- exact target URL
- timestamp and run ID

Stop rule: Any critical finding stops Phase 2.

## Phase 2 Step 5: Run DR Restore Check

Command:

```powershell
C:\Program Files\PowerShell\7\pwsh.exe -File scripts/testing/dr_restore_check.ps1 `
  -WslKubeconfig <path-to-talos-kubeconfig> `
  *> /tmp/phase2-dr.log
```

WSL command:

```bash
pwsh -File scripts/testing/dr_restore_check.ps1 \
  -WslKubeconfig <path-to-talos-kubeconfig> \
  *> "${PHASE2_DIR}/phase2-dr.log"
```

Expected output:

- Pods listed.
- Deployments listed.
- Services listed.
- DR checkpoint message printed.

Evidence capture:

```bash
cp "${PHASE2_DIR}/phase2-dr.log" "${PHASE2_DIR}/phase2-dr-checkpoint.log"
scripts/mock-vault-for-dr-test.sh audit-check \
  > "${PHASE2_DIR}/phase2-mock-vault-audit-check.json"
```

Validation gates:

- Required resources are visible.
- Restore evidence is attached or limitation is explicitly recorded.
- RTO/RPO measurements are present if a real restore is performed.

If FAIL:

```bash
kubectl -n synthetic-enterprise get all \
  > "${PHASE2_DIR}/phase2-dr-failure-resources.txt"
```

Escalate to backup/infrastructure owner if restore evidence is missing or RTO/RPO cannot be measured.

Stop rule: Missing namespace or missing compliance deployment stops Phase 2.

## Phase 2 Step 6: Run Blue-Green Validation

Command:

```powershell
C:\Program Files\PowerShell\7\pwsh.exe -File scripts/testing/blue_green_validate.ps1 `
  -WslKubeconfig <path-to-talos-kubeconfig> `
  -ActiveColor blue `
  -CandidateColor green `
  *> /tmp/phase2-blue-green.log
```

WSL command:

```bash
pwsh -File scripts/testing/blue_green_validate.ps1 \
  -WslKubeconfig <path-to-talos-kubeconfig> \
  -ActiveColor blue \
  -CandidateColor green \
  *> "${PHASE2_DIR}/phase2-blue-green.log"
```

Expected output:

- Deployment readiness shown.
- Rollout status succeeds.
- Endpoints populated.
- Pods listed.
- Rollback command printed.

Evidence capture:

```bash
cp "${PHASE2_DIR}/phase2-blue-green.log" "${PHASE2_DIR}/phase2-blue-green-validation.log"
kubectl -n synthetic-enterprise get endpoints compliance-service \
  > "${PHASE2_DIR}/phase2-blue-green-endpoints.txt"
```

Validation gates:

- Deployment `2/2`.
- Endpoints present.
- No pod restarts.
- Rollback command printed and correct.

If FAIL:

```bash
kubectl -n synthetic-enterprise describe deployment compliance-service \
  > "${PHASE2_DIR}/phase2-blue-green-deploy-describe.txt"
kubectl -n synthetic-enterprise get events --sort-by=.lastTimestamp \
  > "${PHASE2_DIR}/phase2-blue-green-events.txt"
```

Escalate to Ops if endpoint/rollout issues persist after rollback.

## Phase 2 Step 7: Evidence Bundle

Command:

```bash
scripts/capture-all-evidence.sh "${RUN_ID}" > "${PHASE2_DIR}/phase2-auto-evidence.json"

tar -czf "phase2-evidence-bundle-${RUN_ID}.tar.gz" \
  -C /tmp "${RUN_ID}"
```

Expected output:

```text
phase2-evidence-bundle-<run-id>.tar.gz
```

Validation gate:

```bash
tar -tzf "phase2-evidence-bundle-${RUN_ID}.tar.gz" | head
```

If FAIL:

- do not claim evidence captured
- attach raw logs manually
- escalate to ChatGPT execution owner

Upload target:

```text
[ops-evidence-bucket or release ticket attachment]
```

## Final Phase 2 Report Template

```text
Phase 2 Run ID:
Talos context:
Load test: PASS | FAIL | CONDITIONAL
ZAP baseline: PASS | FAIL | CONDITIONAL
DR checkpoint: PASS | FAIL | CONDITIONAL
Blue-green: PASS | FAIL | CONDITIONAL
Evidence bundle:
Known limitations:
Rollback used:
Escalations opened:
Final decision:
```

