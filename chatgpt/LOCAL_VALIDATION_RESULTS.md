# Local Validation Results

## Scope

This report records non-cluster Sprint 8 validation performed while waiting for authoritative Talos credentials.

## Script Parser Validation

Result:

```text
testing ps1 scripts parse cleanly
```

Scripts covered:

- `scripts/testing/run_load_test.ps1`
- `scripts/testing/run_zap_baseline.ps1`
- `scripts/testing/dr_restore_check.ps1`
- `scripts/testing/blue_green_validate.ps1`
- `scripts/testing/pre_week14_checklist.ps1`
- `scripts/testing/sprint7_cluster_smoke.ps1`

## Dry-Run Validation

### Load Test

Command:

```powershell
pwsh -File scripts/testing/run_load_test.ps1 `
  -HostUrl http://127.0.0.1:8000 `
  -Users 5 `
  -SpawnRate 1 `
  -RunTime 10s `
  -DryRun
```

Output:

```text
DRY RUN: Load test
HostUrl: http://127.0.0.1:8000
Users: 5
SpawnRate: 1
RunTime: 10s
ReportPath: chatgpt/sprint-8/load-test-report.html
Docker: False
Locustfile: scripts/testing/load_locustfile.py
RESULT: DRY RUN COMPLETE
```

Result: PASS

### ZAP Baseline

Command:

```powershell
pwsh -File scripts/testing/run_zap_baseline.ps1 `
  -TargetUrl http://127.0.0.1:8000 `
  -DryRun
```

Output:

```text
DRY RUN: ZAP baseline
TargetUrl: http://127.0.0.1:8000
ReportPath: chatgpt/sprint-8/zap-baseline-report.html
Image: zaproxy/zap-stable:latest
RESULT: DRY RUN COMPLETE
```

Result: PASS

### DR Restore Check

Command:

```powershell
pwsh -File scripts/testing/dr_restore_check.ps1 -DryRun
```

Output:

```text
DRY RUN: DR restore checkpoint
Namespace: synthetic-enterprise
WslKubeconfig: ~/.kube/aia-config.yaml
Would capture: pods, deployments, services
RESULT: DRY RUN COMPLETE
```

Result: PASS

### Blue-Green Validation

Command:

```powershell
pwsh -File scripts/testing/blue_green_validate.ps1 -DryRun
```

Output:

```text
DRY RUN: Blue-green validation
Namespace: synthetic-enterprise
App: compliance-service
WslKubeconfig: ~/.kube/aia-config.yaml
Active color: blue
Candidate color: green
Would capture: deployment, rollout status, endpoints, pods
Rollback command: kubectl rollout undo deployment/compliance-service -n synthetic-enterprise
RESULT: DRY RUN COMPLETE
```

Result: PASS

## Bash Utility Validation

Command:

```bash
bash -n scripts/setup-ghcr-auth.sh
bash -n scripts/mock-vault-for-dr-test.sh
bash -n scripts/rollback-to-blue.sh
bash -n scripts/capture-all-evidence.sh
bash -n scripts/verify-evidence-parsing.sh
```

Output:

```text
setup-ghcr-auth.sh OK
mock-vault-for-dr-test.sh OK
rollback-to-blue.sh OK
capture-all-evidence.sh OK
verify-evidence-parsing.sh OK
```

Result: PASS

## Mock Evidence Fixture Validation

Command:

```bash
scripts/verify-evidence-parsing.sh
```

Output:

```text
fixture_valid=true
fixture=tests/fixtures/mock-kubectl-responses.json
keys=context,nodes,deployments,pods,services,endpoints,events,rollout_history,rollout_status
```

Result: PASS

## Remaining External Dependency

Local validation does not prove Sprint 8 against Talos. Execution remains gated on authoritative Talos kubeconfig and matching `~/.talos/config`.
