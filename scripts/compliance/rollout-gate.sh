#!/bin/bash

NAMESPACE="${NAMESPACE:-ordinox-ai}"
DEPLOYMENT="${DEPLOYMENT:-compliance-service}"
TIMEOUT="${TIMEOUT:-120}"
START=$(date +%s)

echo "🚦 Rollout Gate Validation"
echo "Checking $DEPLOYMENT in $NAMESPACE..."
echo ""

while true; do
    NOW=$(date +%s)
    ELAPSED=$((NOW - START))
    
    REPLICAS=$(kubectl -n $NAMESPACE get deployment $DEPLOYMENT -o jsonpath='{.status.replicas}' 2>/dev/null || echo "0")
    READY=$(kubectl -n $NAMESPACE get deployment $DEPLOYMENT -o jsonpath='{.status.readyReplicas}' 2>/dev/null || echo "0")
    
    echo "Status: $READY/$REPLICAS ready (${ELAPSED}s elapsed)"
    
    if [ "$REPLICAS" -gt 0 ] && [ "$READY" -eq "$REPLICAS" ]; then
        echo "✅ VERDICT: GO"
        exit 0
    fi
    
    if [ $ELAPSED -ge $TIMEOUT ]; then
        echo "❌ VERDICT: NO-GO (timeout)"
        exit 1
    fi
    
    sleep 5
done

