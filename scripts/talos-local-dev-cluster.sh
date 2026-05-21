#!/usr/bin/env bash
# Local Talos dev cluster — Docker-provisioner bootstrap.
#
# Stands up a real Talos cluster running in Docker containers on the
# developer's laptop. Identical Talos API + Kubernetes API to prod, so
# all Sprint 6 manifests (NetworkPolicy, RBAC, Kyverno, signed images)
# behave the same way.
#
# Why this exists: prod Talos at 148.251.247.56 is an ops infrastructure
# question (see ops/NEXT_ACTION_DECISION_TREE.md). This script unblocks
# Gemini/ChatGPT/Cursor/Claude Code from waiting on that answer for
# everyday development + integration work.
#
# Usage:
#   bash scripts/talos-local-dev-cluster.sh up         # create cluster
#   bash scripts/talos-local-dev-cluster.sh status     # show state
#   bash scripts/talos-local-dev-cluster.sh down       # tear down
#   bash scripts/talos-local-dev-cluster.sh logs       # tail node logs
#
# Tuning (env vars):
#   CLUSTER_NAME      default: aia-dev
#   K8S_VERSION       default: v1.31.0
#   WORKERS           default: 2
#   CPUS_PER_NODE     default: 2
#   MEMORY_PER_NODE   default: 2048  (MiB)

set -euo pipefail

CLUSTER_NAME="${CLUSTER_NAME:-aia-dev}"
K8S_VERSION="${K8S_VERSION:-v1.31.0}"
WORKERS="${WORKERS:-2}"
CPUS_PER_NODE="${CPUS_PER_NODE:-2}"
MEMORY_PER_NODE="${MEMORY_PER_NODE:-2048}"

CMD="${1:-up}"


require() {
    if ! command -v "$1" >/dev/null 2>&1; then
        echo "ERROR: $1 not on PATH." >&2
        echo "Install:" >&2
        case "$1" in
            talosctl) echo "  https://www.talos.dev/latest/talos-guides/install/talosctl/" >&2 ;;
            docker)   echo "  https://docs.docker.com/get-docker/" >&2 ;;
            kubectl)  echo "  https://kubernetes.io/docs/tasks/tools/" >&2 ;;
        esac
        exit 2
    fi
}


cluster_up() {
    require talosctl
    require docker
    require kubectl

    if ! docker info >/dev/null 2>&1; then
        echo "ERROR: docker daemon not running." >&2
        exit 2
    fi

    if talosctl cluster show --name "${CLUSTER_NAME}" >/dev/null 2>&1; then
        echo "Cluster '${CLUSTER_NAME}' already exists. Use 'down' to recreate."
        cluster_status
        return 0
    fi

    local total_cpu=$(( (1 + WORKERS) * CPUS_PER_NODE ))
    local total_mem=$(( (1 + WORKERS) * MEMORY_PER_NODE ))
    echo "Creating cluster '${CLUSTER_NAME}' — 1 controlplane + ${WORKERS} workers"
    echo "Resources: ${total_cpu} vCPU total, ${total_mem} MiB RAM total"

    # The Docker provisioner writes:
    #   ~/.talos/config            (talosconfig, context: ${CLUSTER_NAME})
    #   ~/.kube/config             (kubeconfig context appended: admin@${CLUSTER_NAME})
    # Both files are merged into the existing ones, so dev's other clusters
    # remain untouched.
    talosctl cluster create \
        --provisioner=docker \
        --name="${CLUSTER_NAME}" \
        --kubernetes-version="${K8S_VERSION}" \
        --workers="${WORKERS}" \
        --cpus="${CPUS_PER_NODE}" \
        --memory="${MEMORY_PER_NODE}"

    echo
    echo "Waiting for Kubernetes API to be Ready..."
    kubectl --context "admin@${CLUSTER_NAME}" \
        wait --for=condition=Ready node --all --timeout=5m

    cluster_status

    cat <<HINTS

Next steps:
    kubectl config use-context admin@${CLUSTER_NAME}
    kubectl apply -f infrastructure/k3s/namespace.yaml
    kubectl apply -f infrastructure/k3s/network-policies-per-agent.yaml
    kubectl apply -f infrastructure/k3s/rbac-per-agent.yaml
    bash scripts/security/audit_rbac.sh

To run Sprint 6 security E2E tests:
    pytest tests/security -m security -v

CAVEAT: the default Talos Docker provisioner ships KubeProxy + Flannel,
which does NOT enforce NetworkPolicy. Sprint 6 policies will be inert
unless you swap to a CNI that enforces (Calico/Cilium). For dev validation
of YAML correctness this is fine; for real enforcement testing, spin up
a kind cluster with Calico or a Talos cluster with Cilium config patches.
See docs/NETWORK-POLICY-TROUBLESHOOTING.md § Step 0.
HINTS
}


cluster_down() {
    require talosctl
    if ! talosctl cluster show --name "${CLUSTER_NAME}" >/dev/null 2>&1; then
        echo "Cluster '${CLUSTER_NAME}' is not running."
        return 0
    fi
    echo "Destroying cluster '${CLUSTER_NAME}'..."
    talosctl cluster destroy --name "${CLUSTER_NAME}"
    # Clean up the kubeconfig context too, so it doesn't dangle.
    kubectl config delete-context "admin@${CLUSTER_NAME}" 2>/dev/null || true
    kubectl config delete-cluster "${CLUSTER_NAME}"     2>/dev/null || true
    echo "Done."
}


cluster_status() {
    require talosctl
    echo
    echo "== talosctl =="
    talosctl cluster show --name "${CLUSTER_NAME}" 2>&1 || echo "(cluster not running)"
    echo
    echo "== kubectl =="
    kubectl --context "admin@${CLUSTER_NAME}" get nodes -o wide 2>&1 || echo "(kubeconfig context missing)"
    echo
    echo "Active kubectl context: $(kubectl config current-context 2>&1)"
}


cluster_logs() {
    require talosctl
    talosctl --context "${CLUSTER_NAME}" -n controlplane-1 logs kubelet --follow
}


case "${CMD}" in
    up)     cluster_up ;;
    down)   cluster_down ;;
    status) cluster_status ;;
    logs)   cluster_logs ;;
    *)
        echo "Usage: $0 {up|down|status|logs}" >&2
        exit 1
        ;;
esac
