# Talos Infrastructure — Next Action Decision Tree

When ops runs `bash ops/talos-triage.sh`, the summary block names a
**VERDICT** that maps to one branch below. Pick the branch, follow the
listed action.

The deployment teams (Gemini, ChatGPT, Cursor, Claude Code) read the
right-hand column to know what they can do *right now*, regardless of
which branch ops is in.

---

## VERDICT A — PRODUCTION READY

```
API_REACHABLE = YES
TALOSCTL_WORKS = YES
```

| Owner | Action | Timeline |
|---|---|---|
| **Ops** | Reply to deployment team thread with: (a) the talosconfig file at `${TALOSCONFIG_PATH}` from the triage report, (b) the CA cert, (c) one-line confirmation `"Verdict A — config attached"`. | within 1 hour |
| **Deployment teams** | `export TALOSCONFIG=<received-file>` → `talosctl --nodes <ip> kubeconfig > ~/.kube/aia-prod.yaml` → `export KUBECONFIG=~/.kube/aia-prod.yaml` → execute `docs/STAGING-DEPLOY-RUNBOOK.md` from Step 0. | begins immediately on reply |

**Sanity check before sharing the talosconfig:**

```bash
talosctl --talosconfig <path> --nodes <ip> version --short
talosctl --talosconfig <path> --nodes <ip> kubeconfig - | head -5
```

If both work, attach the file. Don't paste the contents into Slack —
contains client certs.

---

## VERDICT B — NEEDS CONFIG (API up, no talosconfig)

```
API_REACHABLE = YES
TALOSCONFIG = NO  (no file found on triage host)
```

| Owner | Action | Timeline |
|---|---|---|
| **Ops** | Locate the original Talos installer machine and copy `~/.talos/config` from there. **OR** generate a new config from scratch: `talosctl gen config <cluster-name> https://<ip>:6443 --output-dir talos-config/` and bootstrap. If the cluster was installed by someone else, ask them — config doesn't regenerate, it must come from somewhere. | 2–6 hours |
| **Deployment teams** | Run local dev cluster: `bash scripts/talos-local-dev-cluster.sh up`. Validate all Sprint 6 manifests against it. When ops produces a real config, swap KUBECONFIG and re-run the same `kubectl apply` commands. | start immediately, parallel |

**If Talos was never actually installed on the node:**
Verdict B is misleading — port 50000 is responding to *something* but
maybe not a Talos node. Have ops run on the node itself:
```bash
ssh <ops-jumphost> 'ss -tlnp | grep :50000'
```
If the listener isn't `apid` (Talos's API daemon), the IP belongs to a
different service. Treat as Verdict C.

---

## VERDICT C — NETWORK BLOCKED

```
API_REACHABLE = NO
```

| Owner | Action | Timeline |
|---|---|---|
| **Ops** | 1. Open Hetzner Cloud Console → server `${HETZNER_SERVER_ID}` → Firewall. 2. Add inbound rule: TCP/50000 from ops network CIDR. 3. Verify with `nc -zv <ip> 50000` from a machine in that CIDR. 4. Re-run `talos-triage.sh` to re-verdict. | 30 min |
| **Ops (fallback)** | If firewall rules look correct but port still refused: server might be powered off or Talos service crashed. Check Hetzner server power state; reboot if needed. If Talos itself is broken, escalate to whoever installed it — needs `talosctl reset` from the install machine. | 1–4 hours |
| **Deployment teams** | Run local dev cluster (`bash scripts/talos-local-dev-cluster.sh up`). Validate manifests, run integration tests, etc. **Do not** wait. | start immediately |

---

## VERDICT D — INCONCLUSIVE

```
Any combination that doesn't match A / B / C.
```

| Owner | Action | Timeline |
|---|---|---|
| **Ops** | Re-run triage with `bash -x ops/talos-triage.sh` to capture per-line trace. Attach the full `talos-triage-report.txt` + the `-x` trace to a reply. Escalate to program leadership with a specific question, e.g. *"talosctl reaches the node but `version` returns X — is the CA bundle correct?"* — not "things aren't working". | within 4 hours |
| **Deployment teams** | Local dev cluster, as above. | unblocked |

---

## What every deployment team can do *today*, regardless of verdict

All four teams have the same parallel-track playbook while ops is on the critical path:

```bash
# 1. Stand up a local Talos cluster (90 seconds)
bash scripts/talos-local-dev-cluster.sh up

# 2. Apply the manifests we'd apply in prod
kubectl --context admin@aia-dev apply -f infrastructure/k3s/namespace.yaml
kubectl --context admin@aia-dev apply -f infrastructure/k3s/postgres.yaml
kubectl --context admin@aia-dev apply -f infrastructure/k3s/redis.yaml
kubectl --context admin@aia-dev apply -f infrastructure/k3s/jaeger.yaml
kubectl --context admin@aia-dev apply -f infrastructure/k3s/network-policies-per-agent.yaml
kubectl --context admin@aia-dev apply -f infrastructure/k3s/rbac-per-agent.yaml

# 3. Each team's smoke tests
# Gemini   — backend agents, Sprint 3 RAG pipeline
# ChatGPT  — load + security tests against local backend
# Cursor   — frontend integration against local API
# Claude Code — Sprint 6 E2E security tests (pytest -m security)
```

When ops produces a prod talosconfig, the SAME manifests apply unchanged.
Anything the local validation catches is one less surprise in prod.

> **Known caveat — Sprint 6 enforcement on the local cluster.** Talos's
> default Docker provisioner uses Flannel, which doesn't enforce
> NetworkPolicy. The local cluster validates YAML correctness +
> integration paths, but doesn't enforce egress restrictions. To exercise
> the actual NetworkPolicy enforcement, use a kind cluster with Calico
> (`kind create cluster --config infrastructure/security/kind-calico.yaml`)
> or a Talos cluster with Cilium patches. See
> `docs/NETWORK-POLICY-TROUBLESHOOTING.md` § Step 0 for the deny-all
> probe that detects whether your local CNI enforces.

---

## Escalation criteria

Escalate to program leadership when **any** of the following is true:

- Verdict D persists across two triage re-runs separated by 4+ hours.
- Verdict C and Hetzner support hasn't responded in 24 hours.
- Verdict B but no one can find or generate a valid talosconfig.
- Same Verdict has been the blocker for 48+ hours.

When escalating, attach:

1. Latest `talos-triage-report.txt`
2. The specific question or decision needed (not "please help")
3. The cost of further delay (which downstream teams are now idle)
4. The local-dev workaround status (what's working without prod Talos)

---

## Do NOT do these things

- Don't re-send the original "CRITICAL" memo. The triage script + this
  decision tree replaces it.
- Don't run another round of "standing by" responses. Either ops has a
  verdict or they don't — if not, escalate.
- Don't paste a talosconfig file into a public channel. It contains
  client certificates.
- Don't disable the Hetzner firewall entirely as a "temporary" fix.
  Open the specific port from the specific CIDR.
