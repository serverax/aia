#!/bin/bash
# Run after provision-cluster-full.sh. Dumps everything needed to diagnose
# cluster state. Paste the output back into the conversation.

KUBECONFIG_PATH="$HOME/.kube/aia-config.yaml"
export KUBECONFIG="$KUBECONFIG_PATH"

if [ ! -f "$KUBECONFIG_PATH" ]; then
  echo "ERROR: $KUBECONFIG_PATH not found - did provisioning complete step 3?"
  exit 1
fi

echo "═══════════════════════════════════════════════════════"
echo "  CLUSTER VERIFICATION"
echo "  $(date)"
echo "═══════════════════════════════════════════════════════"

echo ""; echo "── Nodes ──"
kubectl get nodes -o wide

echo ""; echo "── synthetic-enterprise namespace ──"
kubectl get all -n synthetic-enterprise

echo ""; echo "── Not-running pods (cluster-wide) ──"
kubectl get pods -A --no-headers | awk '$4!="Running" && $4!="Completed"' || echo "(all running)"

echo ""; echo "── Recent warning events ──"
kubectl get events -A --field-selector type=Warning --sort-by=.lastTimestamp 2>/dev/null \
  | tail -30 || true

echo ""; echo "── Resource pressure on nodes ──"
kubectl top nodes 2>/dev/null || echo "(metrics-server not ready yet)"

echo ""; echo "── Helm releases ──"
helm list -A 2>/dev/null || true

echo ""; echo "═══════════════════════════════════════════════════════"
echo "  Done. Paste the above back into the conversation."
echo "═══════════════════════════════════════════════════════"
