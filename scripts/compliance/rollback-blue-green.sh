#!/bin/bash

NAMESPACE="synthetic-enterprise"
INGRESS="compliance-service-ingress"
DEPLOYMENT="compliance-service"
DRY_RUN=${1:-false}

echo "🔄 Rolling back to blue (100%)..."
echo ""

# Reset canary weight
echo "Step 1: Resetting canary weight to 0%..."
if [ "$DRY_RUN" == "true" ]; then
    echo "[DRY RUN] kubectl -n $NAMESPACE annotate ingress $INGRESS nginx.ingress.kubernetes.io/canary-weight='0' --overwrite"
else
    kubectl -n $NAMESPACE annotate ingress $INGRESS nginx.ingress.kubernetes.io/canary-weight='0' --overwrite
    echo "✅ Done"
fi

echo ""

# Undo deployment
echo "Step 2: Undoing deployment..."
if [ "$DRY_RUN" == "true" ]; then
    echo "[DRY RUN] kubectl -n $NAMESPACE rollout undo deployment/$DEPLOYMENT"
else
    kubectl -n $NAMESPACE rollout undo deployment/$DEPLOYMENT
    echo "✅ Done"
fi

echo ""

# Wait for rollout
if [ "$DRY_RUN" != "true" ]; then
    echo "Step 3: Waiting for rollout..."
    kubectl -n $NAMESPACE rollout status deployment/$DEPLOYMENT --timeout=120s
    echo "✅ Rollout complete"
fi

echo ""
echo "✅ Rollback successful!"

