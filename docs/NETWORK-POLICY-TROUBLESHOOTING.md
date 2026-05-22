# NetworkPolicy Troubleshooting Guide

Ops reference for the `ordinox-ai` namespace. Use this when a
pod can't reach Redis, an external API call hangs, or a fresh policy
apply didn't seem to change anything.

> **Single most common cause of false positives:** your CNI doesn't
> enforce NetworkPolicies at all. Skip to [§ Step 0](#step-0-confirm-your-cni-actually-enforces-networkpolicy)
> before you debug anything else.

---

## TL;DR — Five commands to keep in your scrollback

```bash
# 0. List policies that apply to a pod
kubectl describe pod -n ordinox-ai <pod>      | grep -A2 'Labels'
kubectl get networkpolicies -n ordinox-ai -o wide

# 1. Watch a probe pod do DNS + TCP from inside the namespace
kubectl run -n ordinox-ai probe --rm -it \
  --image=nicolaka/netshoot --labels=app=echo-agent --restart=Never -- bash

# 2. Confirm CoreDNS is reachable + serving
kubectl -n kube-system get pods -l k8s-app=kube-dns
kubectl -n kube-system logs -l k8s-app=kube-dns --tail=20 --prefix

# 3. Show what kube-system labels actually exist (NP selectors depend on these)
kubectl get ns kube-system -o jsonpath='{.metadata.labels}' ; echo

# 4. Compare desired vs deployed RBAC + policies
bash scripts/security/audit_rbac.sh
python scripts/security/generate_policies.py     # regenerates from capabilities.yaml
git diff infrastructure/k3s/network-policies-per-agent.yaml
```

---

## Step 0 — Confirm your CNI actually enforces NetworkPolicy

**This is the #1 source of "policy applied but nothing changed" reports.**

| CNI | Enforces NetworkPolicy by default? |
|---|---|
| **k3s default (flannel)** | ❌ **No.** Policies are accepted but inert. |
| Calico | ✅ Yes |
| Cilium | ✅ Yes |
| Talos default (Flannel + KubeProxy) | ❌ No without additional CNI |
| Talos with Cilium | ✅ Yes |
| Weave Net | ✅ Yes |

**Quick check:**

```bash
# 1. What CNI is running?
kubectl -n kube-system get pods -o wide \
  | grep -E 'calico|cilium|flannel|weave|kube-router'

# 2. Apply a deliberately broken deny-all policy in a test namespace and
#    see if a probe pod loses connectivity. If it stays connected, the CNI
#    is ignoring policies.
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Namespace
metadata: { name: np-test }
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata: { name: deny-all, namespace: np-test }
spec:
  podSelector: {}
  policyTypes: [Ingress, Egress]
EOF

kubectl run -n np-test probe --rm -i --image=busybox:1.36 --restart=Never \
  --command -- sh -c 'wget -q --timeout=3 http://1.1.1.1 ; echo "exit=$?"'
# Expected with enforcement on: timeout, exit non-zero
# Got "exit=0"? Your CNI doesn't enforce policies.

kubectl delete ns np-test
```

**If enforcement is off**, you have two options:

1. **(Recommended) Switch CNI to Calico or Cilium** before relying on any of
   our NetworkPolicy artifacts. The whole Sprint 6 security model assumes
   enforcement. Without it, the policies are documentation, not control.
2. **(Stopgap)** Layer Kyverno deny policies on top so cluster-wide
   invariants still hold. NetworkPolicy-level egress filtering is lost.

---

## How NetworkPolicy actually works (recall before debugging)

Three rules of thumb that catch most misunderstandings:

1. **Default is allow, until the first policy selects a pod.** A pod with
   zero matching policies has unrestricted ingress + egress.
2. **Once selected by any policy, that pod is default-deny for the policy
   types listed (`Ingress`, `Egress`, or both).** Other policies that
   select the same pod can re-allow specific traffic — policies are
   **additive (union)**.
3. **`podSelector: {}` matches every pod in the namespace.** Combined with
   `policyTypes: [Ingress, Egress]` and no `egress`/`ingress` keys, this
   is the universal deny-all baseline.

In our setup:
- `infrastructure/k3s/namespace.yaml` has a `default-deny-all` NetworkPolicy.
  Once applied, **every pod** in `ordinox-ai` is default-deny.
- `infrastructure/k3s/namespace.yaml` also has `allow-internal` which
  re-allows same-namespace traffic + DNS to kube-system.
- `infrastructure/k3s/network-policies-per-agent.yaml` adds per-agent
  egress rules (external API access for orchestrator/analyst, etc.).
- All three are applied together. The union is what each pod can do.

---

## Failure scenarios

### Scenario 1 — Agent can't reach `redis.ordinox-ai.svc.cluster.local`

**Symptoms**
- Agent logs show `redis.exceptions.ConnectionError: Error -2 connecting to redis...`
- Or `getaddrinfo: Name or service not known`

**Diagnosis (in order)**

```bash
# A. Is DNS even working?
kubectl run -n ordinox-ai dns-probe --rm -i \
  --image=busybox:1.36 --labels=app=echo-agent --restart=Never \
  -- nslookup redis.ordinox-ai.svc.cluster.local
```

- ❌ `can't resolve` → go to **Scenario 2** (DNS).
- ✅ Resolves to a `10.x.x.x` → DNS works; continue.

```bash
# B. Can we actually TCP to it?
kubectl run -n ordinox-ai tcp-probe --rm -i \
  --image=busybox:1.36 --labels=app=echo-agent --restart=Never \
  -- sh -c 'nc -zv -w 3 redis 6379'
```

- ❌ `timed out` → NetworkPolicy is blocking. Continue.
- ✅ `succeeded` → it's an application-level issue (auth, schema, etc.).

```bash
# C. What policies select this pod?
kubectl get networkpolicies -n ordinox-ai -o json \
  | jq '.items[] | {name:.metadata.name, podSelector:.spec.podSelector, policyTypes:.spec.policyTypes}'

# D. Does the agent's Deployment actually carry the label our NP expects?
kubectl get deploy -n ordinox-ai echo-agent -o jsonpath='{.spec.template.metadata.labels}'
```

**Common root causes**
- Deployment template labels don't include `app: echo-agent` (NP selector misses → falls under default-deny only).
- Redis Service has a different `app=` label than the NP expects.
- Redis is in a different namespace and the NP only allows same-namespace.

**Fix**
- Add `app: <agent-name>-agent` to the Deployment's `spec.template.metadata.labels`.
- Or update `capabilities.yaml` to match the actual labels + regenerate.

**Verify**

```bash
kubectl rollout restart deploy/echo-agent -n ordinox-ai
# Then re-run probe A and B above.
```

---

### Scenario 2 — DNS lookups time out / return NXDOMAIN

**Symptoms**
- `nslookup redis.ordinox-ai.svc.cluster.local` from inside a pod
  hangs or returns `;; connection timed out; no servers could be reached`
- BUT `nslookup 8.8.8.8` works (or fails differently)

**The Day 8 bug, in one sentence:** if the per-agent NetworkPolicy uses
`namespaceSelector: { matchLabels: { name: kube-system } }`, **DNS egress
is silently denied on every cluster that didn't manually label kube-system.**

The canonical selector since Kubernetes 1.22 is `kubernetes.io/metadata.name`,
which the apiserver auto-applies:

```yaml
# WRONG (silent failure on most clusters)
namespaceSelector:
  matchLabels:
    name: kube-system

# RIGHT
namespaceSelector:
  matchLabels:
    kubernetes.io/metadata.name: kube-system
```

**Diagnosis**

```bash
# 1. Does kube-system carry the auto-applied label?
kubectl get ns kube-system -o jsonpath='{.metadata.labels}' ; echo
# Look for "kubernetes.io/metadata.name":"kube-system"

# 2. What does the agent's NP actually allow for DNS?
kubectl get networkpolicy <agent>-agent-egress -n ordinox-ai -o yaml \
  | grep -A4 'namespaceSelector'
```

**Fix in our codebase**
The generator (`scripts/security/generate_policies.py`) emits the correct
selector and we have a regression test
(`tests/security/test_policy_generator.py::test_network_policy_dns_rule_uses_canonical_namespace_label_REGRESSION`).
If you find DNS broken, the fix is almost certainly **not** to edit the
generated YAML by hand — regenerate from `capabilities.yaml`:

```bash
python scripts/security/generate_policies.py
kubectl apply -f infrastructure/k3s/network-policies-per-agent.yaml
```

**Fix on the cluster directly (only if you can't redeploy)**
Label kube-system so the old selector starts working:
```bash
kubectl label ns kube-system name=kube-system
```
This is a stopgap; commit the proper fix to the generator.

**Verify**

```bash
kubectl run -n ordinox-ai dns-probe --rm -i \
  --image=busybox:1.36 --labels=app=echo-agent --restart=Never \
  -- sh -c '
    nslookup kubernetes.default
    nslookup redis.ordinox-ai.svc.cluster.local
  '
# Both should resolve in <1s.
```

---

### Scenario 3 — Pod can resolve DNS but can't reach the resolved IP

**Symptoms**
- `nslookup` returns `Address: 10.43.0.5` (or similar)
- `nc -zv 10.43.0.5 6379` times out

**Diagnosis**

```bash
# Is there an in-cluster egress rule for the destination?
kubectl get networkpolicy <agent>-agent-egress -n ordinox-ai -o yaml
# Look for an egress entry with the destination's podSelector
```

**Common root causes**
- The destination's `podSelector` label changed (e.g. Redis chart renamed labels).
- The destination is in a different namespace; per-agent NP only covers same-namespace by default.
- Pod IPs vs Service IPs: our NPs use `podSelector` (pod-targeted). If you're seeing connections going to the Service ClusterIP, kube-proxy resolves it to a pod IP first, then NP applies to the pod. Should still work, but verify with `kubectl get endpoints`.

**Fix**
- Update `capabilities.yaml` services section if labels changed.
- Add a `namespaceSelector` to the egress rule if destination is cross-namespace.
- Regenerate + reapply.

---

### Scenario 4 — Pod can reach in-cluster services but external (Anthropic) is blocked

**Symptoms**
- LLM calls fail with `ConnectionError` or `getaddrinfo failed`.
- Specifically affects `orchestrator-agent` or `analyst-agent`.

**Diagnosis**

```bash
# A. Is the agent's NP supposed to allow external?
grep -A5 'external_allow' infrastructure/security/capabilities.yaml | grep -B1 anthropic

# B. Is the ipBlock rule actually in the deployed NP?
kubectl get networkpolicy orchestrator-agent-egress -n ordinox-ai -o yaml \
  | grep -A6 'ipBlock'
```

**Common root causes**
- Agent isn't listed under `external_allow: [anthropic]` in capabilities.yaml.
- The egress rule is there but the destination IP falls under the RFC 1918 `except` list (rare — Anthropic's IPs are public).
- DNS resolves `api.anthropic.com` but the resolved IP is blocked by an upstream firewall (cluster-external).

**Fix**

```bash
# Add the agent to external_allow in capabilities.yaml, then:
python scripts/security/generate_policies.py
kubectl apply -f infrastructure/k3s/network-policies-per-agent.yaml
```

**Verify**

```bash
kubectl exec -n ordinox-ai <orchestrator-pod> -- \
  curl -sS -o /dev/null -w "%{http_code}\n" \
  https://api.anthropic.com/v1/messages
# Expect 401 (no auth) — not "Could not resolve host" or "Connection timed out".
# 401 = network path works, just no API key.
```

---

### Scenario 5 — Readiness/liveness probes failing

**Symptoms**
- Pod cycles in `CrashLoopBackOff` or `Running 0/1`
- `kubectl describe pod` shows `Readiness probe failed: connection refused` or `timeout`

**Diagnosis**
Kubelet probes originate from the **node** (the host network), not from
inside the cluster network. Most CNIs treat kubelet → pod traffic as
node-local and bypass NetworkPolicy ingress rules. Some don't.

```bash
# Which CNI?
kubectl -n kube-system get pods -o wide | grep -E 'calico|cilium|flannel'

# Test from inside a pod (NP applies to this path)
kubectl run -n ordinox-ai probe --rm -i \
  --image=busybox:1.36 --labels=app=client-test --restart=Never \
  -- wget -q -T 3 -O - http://echo-agent:8000/health
```

**Common root causes**
- Cilium with strict mode — kubelet probes blocked. Fix: add `from: [{ podSelector: {}, namespaceSelector: {} }]` ingress rule, or use Cilium's L7 policy with `kubelet-allowed`.
- App's `/health` endpoint genuinely failing — `kubectl logs <pod>` reveals truth.
- Wrong port in probe spec.

**Fix**
- Add an explicit ingress rule for the agent allowing same-namespace + kubelet.
- We didn't generate per-agent ingress rules in Sprint 6 Day 8 — the `allow-internal` policy in namespace.yaml covers same-namespace traffic, and most CNIs allow kubelet probes via node-network exemption.

---

### Scenario 6 — "I applied the policy but nothing changed"

**Symptoms**
- `kubectl apply -f network-policies-per-agent.yaml` succeeded
- Pods still reach previously-blocked destinations

**Diagnosis (in order)**

```bash
# A. Did the NP actually land?
kubectl get networkpolicy -n ordinox-ai

# B. Does it select the pods you think it does?
kubectl get networkpolicy <agent>-agent-egress -n ordinox-ai \
  -o jsonpath='{.spec.podSelector}' ; echo
kubectl get pod -n ordinox-ai -l app=<agent>-agent

# C. Does your CNI actually enforce? (Go back to Step 0.)
```

**Common root causes**
- **CNI doesn't enforce.** Most common. See Step 0.
- Pod doesn't have the label the NP selects on.
- Pod was already running when NP was applied — some CNIs only apply NPs at pod creation. `kubectl rollout restart deploy/<agent>` forces re-evaluation.

---

### Scenario 7 — Policy regenerated, audit says drift, but no obvious cause

**Symptoms**
- `bash scripts/security/audit_rbac.sh` reports `EXTRA` resources
- You don't recognize the names

**Diagnosis**

```bash
# Which manifest defines these resources?
git grep -l "name: <suspicious-name>" infrastructure/ services/

# Did somebody hand-apply something?
kubectl get <kind> <name> -n ordinox-ai -o yaml \
  | grep -E 'last-applied|creationTimestamp|annotations'
```

**Common root causes**
- Sprint 7 work (compliance-service) shipped its own SA/Role and you haven't added it to `capabilities.yaml`.
- A previous experiment left orphan resources.
- Helm chart from another team created its own RBAC.

**Fix**
- If intentional → add the resource to `capabilities.yaml` so audit stops flagging it.
- If orphan → `kubectl delete <kind> <name> -n ordinox-ai`.

---

## Validation procedure for a fresh apply

Run this after `kubectl apply -f infrastructure/k3s/network-policies-per-agent.yaml`:

```bash
set -e

NS=ordinox-ai

# 1. Policies are present
kubectl get networkpolicy -n "$NS" \
  | grep -E 'analyst-agent-egress|compliance-agent-egress|echo-agent-egress|orchestrator-agent-egress' \
  | wc -l   # expect 4

# 2. RBAC matches capabilities.yaml
bash scripts/security/audit_rbac.sh

# 3. DNS works from each agent's pod selector
for agent in echo orchestrator analyst compliance; do
  echo "=== $agent dns probe ==="
  kubectl run -n "$NS" "${agent}-dns-probe" --rm -i \
    --image=busybox:1.36 \
    --labels=app="${agent}-agent" \
    --restart=Never \
    -- nslookup kubernetes.default 2>&1 | head -10
done

# 4. In-cluster service reachability (just redis, fastest signal)
for agent in echo orchestrator analyst compliance; do
  echo "=== $agent → redis ==="
  kubectl run -n "$NS" "${agent}-redis-probe" --rm -i \
    --image=busybox:1.36 \
    --labels=app="${agent}-agent" \
    --restart=Never \
    -- sh -c 'nc -zv -w 3 redis 6379' 2>&1
done

# 5. External egress should work for orchestrator + analyst, fail for echo + compliance
for agent in orchestrator analyst; do
  echo "=== $agent → anthropic (should reach) ==="
  kubectl run -n "$NS" "${agent}-ext-probe" --rm -i \
    --image=curlimages/curl:8.10.1 \
    --labels=app="${agent}-agent" \
    --restart=Never \
    -- curl -sS -o /dev/null -w "%{http_code}\n" --max-time 5 https://api.anthropic.com/v1/messages
  # Expect 401
done
for agent in echo compliance; do
  echo "=== $agent → anthropic (should be blocked) ==="
  kubectl run -n "$NS" "${agent}-ext-probe" --rm -i \
    --image=curlimages/curl:8.10.1 \
    --labels=app="${agent}-agent" \
    --restart=Never \
    -- curl -sS -o /dev/null -w "%{http_code}\n" --max-time 5 https://api.anthropic.com/v1/messages \
    || true
  # Expect non-zero exit / timeout
done
```

---

## Integration with the Sprint 6 toolchain

The three tools work as a tight loop. If anything looks wrong, walk it:

```
capabilities.yaml  ──[generate_policies.py]──>  network-policies-per-agent.yaml
        │                                                 │
        │                                                 ▼
        │                                          kubectl apply
        │                                                 │
        ▼                                                 ▼
   audit_rbac.py  <─────[ kubectl get ]─────  live cluster state
```

- **Source change** → edit `infrastructure/security/capabilities.yaml`.
- **Regenerate** → `python scripts/security/generate_policies.py`. Diff the output; commit if intentional.
- **Apply** → `kubectl apply -f infrastructure/k3s/network-policies-per-agent.yaml -f infrastructure/k3s/rbac-per-agent.yaml`.
- **Audit** → `bash scripts/security/audit_rbac.sh`. Exit 0 = clean.
- **Drift detected** → either fix the cluster (re-apply) or update `capabilities.yaml` if the cluster state is correct.

Hand-edits to `network-policies-per-agent.yaml` are an audit finding — the
header comment at the top of the file says `AUTOGENERATED`. If you change
it directly, `audit_rbac.sh` will catch it the next time it runs.

---

## Quick reference — useful images for probe pods

| Image | Use |
|---|---|
| `busybox:1.36` | nslookup, nc, wget — minimal |
| `nicolaka/netshoot` | curl, dig, tcpdump, mtr — full toolkit |
| `curlimages/curl:8.10.1` | curl-only, small + fast |
| `alpine:3.20` | `apk add` whatever you need, persistent test pod |

Always label probe pods to match an agent NP's `podSelector`, otherwise
you get default-deny behavior and conclude things are broken when they
aren't:

```bash
kubectl run probe -n ordinox-ai \
  --rm -i --restart=Never \
  --image=nicolaka/netshoot \
  --labels=app=echo-agent \
  -- bash
```

---

## When to escalate vs fix in place

| Situation | Action |
|---|---|
| One scenario above matches → follow its fix | Self-serve |
| Step 0 reveals CNI doesn't enforce | Page platform team — CNI swap is cluster-wide |
| Audit drift you didn't cause | Check git blame on `capabilities.yaml` + recent kubectl history |
| DNS works for some pods, not others | Likely pod-label mismatch — check Deployment template labels |
| Worked yesterday, broken today | `kubectl get events -n ordinox-ai --sort-by='.lastTimestamp' \| tail -30` |
| Test pod works, real agent doesn't | Real agent's labels probably differ — `kubectl get deploy <agent> -o jsonpath='{.spec.template.metadata.labels}'` |
