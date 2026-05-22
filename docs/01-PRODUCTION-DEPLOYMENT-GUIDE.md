# Production Deployment Guide - v1.0

## Overview
Complete guide for deploying compliance-service with blue-green traffic splitting.

## Quick Start

### Pre-Deployment
```bash
bash scripts/compliance/rollout-gate.sh  # Should show: ✅ VERDICT: GO
python3 tests/compliance/test-traffic-ramp.py  # Should show: 5/5 tests passed
```

### Deployment Phases

**Phase 1: 0% Canary (Blue Only)**
```bash
kubectl -n synthetic-enterprise get ingress synthetic-enterprise-ingress \
  -o jsonpath='{.metadata.annotations.nginx\.ingress\.kubernetes\.io/canary-weight}'
# Expected: 0
```

**Phase 2: 5% Canary**
```bash
kubectl -n synthetic-enterprise annotate ingress synthetic-enterprise-ingress \
  nginx.ingress.kubernetes.io/canary-weight='5' --overwrite
sleep 300
```

**Phase 3: 25% Canary**
```bash
kubectl -n synthetic-enterprise annotate ingress synthetic-enterprise-ingress \
  nginx.ingress.kubernetes.io/canary-weight='25' --overwrite
sleep 300
```

**Phase 4: 50% Canary**
```bash
kubectl -n synthetic-enterprise annotate ingress synthetic-enterprise-ingress \
  nginx.ingress.kubernetes.io/canary-weight='50' --overwrite
sleep 300
```

**Phase 5: 100% Promotion**
```bash
kubectl -n synthetic-enterprise annotate ingress synthetic-enterprise-ingress \
  nginx.ingress.kubernetes.io/canary-weight='100' --overwrite
echo "✅ New version is 100% production!"
```

## Rollback

```bash
bash scripts/compliance/rollback-blue-green.sh false
```

## Monitoring

```bash
# Grafana
kubectl port-forward -n monitoring svc/grafana 3000:3000
# http://localhost:3000

# Prometheus
kubectl port-forward -n monitoring svc/kube-prometheus-stack-prometheus 9090:9090
# http://localhost:9090
```
