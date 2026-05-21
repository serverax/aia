# URGENT: Talos Cluster Access Required for Sprint 8

Current state: deployment and testing are blocked because the available context is not the authoritative Talos context for the target Sprint 8 cluster.

## Required From Infrastructure Owner

Please provide:

- Talos Kubernetes kubeconfig for the `148.251.247.56` cluster.
- Matching `~/.talos/config` with Talos client certificates.
- Expected Kubernetes context name, for example `talos-synthetic-enterprise`.
- Expected Talos context name.
- Confirmation that Kubernetes workload operations should continue to use `kubectl` against the Talos kubeconfig.

## Why This Is Blocking

Sprint 8 validation must run against the Talos cluster, not an unrelated AKS or stale local context. Without authoritative credentials, ingress, DNS, and service validation evidence is not release-grade.

## Immediate Verification After Receipt

```bash
export KUBECONFIG=<path-to-talos-kubeconfig>

echo "=== context ==="
kubectl config current-context

echo "=== nodes ==="
kubectl get nodes -o wide

echo "=== talosctl ==="
talosctl version
```

If all three pass, Sprint 8 validation resumes immediately.

## Access Model Clarification

Talos does not use SSH for node access. Use:

- `kubectl` for Kubernetes workloads: deployments, services, ingress, jobs, secrets, logs.
- `talosctl` for node/OS diagnostics: machine config, Talos service logs, dmesg, generated kubeconfig.

Do not mechanically replace `kubectl` with `talosctl` in Sprint 8 workload scripts.

## Requested Deadline

Provide credentials today so Sprint 8 can continue without carrying invalid cluster evidence.
