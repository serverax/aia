# Pre-Deploy Safety Gate

Run `bash scripts/security/pre_deploy_check.sh` before any deployment to
`ordinox-ai`. The gate aggregates four to five checks into a single GO /
NO-GO verdict with a machine-readable JSON report.

## Quick usage

```bash
# Offline check — runs against committed manifests + capabilities.yaml
bash scripts/security/pre_deploy_check.sh
echo $?    # 0 = GO, 1 = NO-GO, 2 = ERROR

# Live check — also audits the cluster's deployed RBAC
export KUBECONFIG=~/.kube/aia-config.yaml
bash scripts/security/pre_deploy_check.sh --live

# CI mode — silent except findings, JSON ends up at $REPORT_FILE
REPORT_FILE=/tmp/gate.json \
  bash scripts/security/pre_deploy_check.sh --quiet
```

## What it checks

| # | Check | Source | What blocks deploy |
|---|---|---|---|
| 1 | **Capability validator** | `scripts/security/capability_validator.py` | Malformed `capabilities.yaml` (missing fields, invalid k8s names, undefined service refs, empty selectors, bad ports) |
| 2 | **Generator drift** | regenerate + diff against committed `network-policies-per-agent.yaml` + `rbac-per-agent.yaml` | Committed generator outputs don't match what `capabilities.yaml` would currently produce |
| 3 | **Policy runtime tests** | `pytest tests/security/test_policies_runtime.py` | Simulator says generated NetworkPolicies don't permit what capabilities declares (or permit more) |
| 4 | **Manifest dry-run** | `kubectl apply --dry-run=client -f` over `infrastructure/k3s/*.yaml` | Any manifest fails client-side schema validation. CRD-dependent manifests (sigstore, Kyverno) produce a warning, not block — they need server-side validation post-CRD-install. |
| 5 | **RBAC audit** (`--live` only) | `scripts/security/audit_rbac.py` | MISSING or MISMATCH between cluster state and `capabilities.yaml`. EXTRA resources produce a warning. |

## Severity → verdict

| Aggregate state | Verdict | Exit code |
|---|---|---|
| Any **CRITICAL** finding | NO-GO | 1 |
| Only WARNING / INFO findings (or none) | GO | 0 |
| Script itself crashes (missing tool, parse error, etc.) | ERROR | 2 |

## Exit codes vs CI

```yaml
# .github/workflows/ci.yml
jobs:
  pre-deploy-gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install -r requirements-dev.txt
      - name: Pre-deploy safety gate
        run: bash scripts/security/pre_deploy_check.sh
        # Exit-1 fails the job — blocks the merge / deploy.
      - name: Upload gate report
        if: always()    # always upload, even on NO-GO
        uses: actions/upload-artifact@v4
        with:
          name: pre-deploy-report
          path: /tmp/pre_deploy_check.json
```

For a Flux GitOps flow, run the gate as a pre-commit hook OR in CI on the
PR that updates `clusters/ordinox-ai/`. Letting Flux reconcile a deploy
that the gate would reject means you found out at the cluster, not in
review.

## JSON report schema

```jsonc
{
  "timestamp": "2026-05-21T23:20:27+00:00",  // UTC ISO-8601
  "mode": "offline" | "live",
  "verdict": "GO" | "NO-GO",
  "exit_code": 0 | 1,
  "summary": {
    "critical": 0,
    "warning": 0,
    "info": 5
  },
  "checks": [
    {
      "check": "capability_validator" | "generator_drift" | "policy_runtime_tests"
             | "manifest_dry_run" | "rbac_audit",
      "status": "PASS" | "FAIL" | "WARN" | "SKIP",
      "severity": "critical" | "warning" | "info",
      "message": "human-readable summary"
    }
    // ... one entry per check that ran
  ]
}
```

Consume this in CI to surface findings:

```bash
# Show only the failures
jq '.checks[] | select(.status=="FAIL")' /tmp/pre_deploy_check.json
```

## Environment overrides

| Variable | Default | Purpose |
|---|---|---|
| `CAPABILITIES` | `infrastructure/security/capabilities.yaml` | Path to capabilities file |
| `MANIFEST_DIR` | `infrastructure/k3s` | Where to find `*.yaml` for dry-run |
| `NETWORK_POLICIES_FILE` | `infrastructure/k3s/network-policies-per-agent.yaml` | Generated NP file to diff against |
| `RBAC_FILE` | `infrastructure/k3s/rbac-per-agent.yaml` | Generated RBAC file to diff against |
| `REPORT_FILE` | `/tmp/pre_deploy_check.json` | Where the JSON report lands |
| `PYTHON` | auto-detect (`python3` / `python` / `py`) | Override interpreter |

## Common findings and fixes

| Finding | Fix |
|---|---|
| `UNDEFINED_SERVICE` in capability_validator | Add the missing service to `services:` block, OR fix the agent's `egress_allow` typo |
| `EMPTY_POD_SELECTOR` | Every agent must have `pod_selector: {app: <name>}` |
| `INVALID_NAMESPACE_NAME` | k8s requires lowercase RFC-1123 DNS labels (no underscores, no caps) |
| Generator drift | Run `python scripts/security/generate_policies.py` then commit the regenerated files |
| Policy runtime FAIL | An expected reachability is broken. Check `tests/security/test_policies_runtime.py::TestGeneratedPolicies` failure messages — they name the agent + destination |
| Manifest dry-run FAIL on `cluster-image-policy.yaml` / `kyverno-policies.yaml` | Expected pre-cluster: these need their CRDs installed. Re-run with `--live` after `helm install` of sigstore + Kyverno |
| RBAC MISMATCH | Someone `kubectl edit`-ed a Role. Re-apply `infrastructure/k3s/rbac-per-agent.yaml` to overwrite. |
| RBAC EXTRA | A resource exists in the cluster that capabilities.yaml doesn't declare. Either add it to capabilities or `kubectl delete` it. |

## Local development tips

- The gate writes color-free output suitable for log files. Pipe through `less -R` if you want pagination.
- The gate doesn't modify anything in the repo or cluster. Re-run as often as needed.
- `--quiet` is for CI; for local debugging, omit it — the per-check headers (`── 1/5 capability validator ──`) make it easy to skim where things fail.
- Each check is independent. If you want to run just one, call its underlying tool directly:
  - `python -m scripts.security.capability_validator`
  - `python -m scripts.security.audit_rbac --from-json <snapshot>`
  - `pytest tests/security/test_policies_runtime.py -v`

## Tests

The gate itself is tested:

- `tests/security/test_capability_validator.py` — 24 unit tests covering every validator rule
- `tests/security/test_pre_deploy_check.py` — 13 integration tests driving the bash script under various states (clean, drift, broken capabilities, bad CLI args, etc.)

Run them:

```bash
pytest tests/security/test_capability_validator.py tests/security/test_pre_deploy_check.py -v
```

Integration tests take ~4 minutes because each test spawns the gate as a
subprocess, and each gate run spawns multiple Python subprocesses for its
check helpers. That's the cost of testing the full integrated pipeline;
worth it.

## Limitations / non-goals

- **Doesn't deploy.** The gate is a pre-flight check, not a deploy tool.
  `kubectl apply` is your responsibility.
- **Doesn't validate Flux Kustomizations.** If you use the Flux variant
  runbook (`docs/STAGING-DEPLOY-RUNBOOK-FLUX.md`), validate your
  `clusters/ordinox-ai/*.yaml` Kustomization manifests separately — they
  reference paths the gate doesn't traverse.
- **CRD-dependent manifests (sigstore, Kyverno) only validate client-side
  syntax.** Full validation requires server-side dry-run against a cluster
  that has the CRDs installed. The gate emits a warning, not a block, for
  these in offline mode.
- **No real cluster network reachability test.** That's what
  `tests/security/test_networkpolicy_blocks_external.py` does in `--live`
  mode against a deployed pod. The gate's policy runtime check uses the
  simulator instead, which is faster and cluster-independent.
